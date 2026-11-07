/**
 * PARI LISTEN — Cloudflare Worker (webhook Telegram)
 * Relais uniquement : allowlist chat_id, parse commande, ACK, dispatch GitHub.
 * Miroir de parse.py. Zero calcul, zero Dixon-Coles.
 * v4.7 codebook : /marches = hint du jour (pas stub O/U2.5,MT2).
 *
 * Secrets wrangler (jamais dans git) :
 *   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_WEBHOOK_SECRET, GITHUB_DISPATCH_TOKEN
 * Vars wrangler.toml :
 *   GH_OWNER, GH_REPO, GH_WORKFLOW, GH_REF
 */

const KNOWN = new Set([
  "start", "capture", "bankroll", "budget", "surticket", "combos",
  "marches", "marchés",
  "valider-1", "valider-2", "valider1", "valider2", "approve",
  "data", "radar", "pack", "match", "status", "roi", "stop",
]);
const LOCAL = new Set(["help", "aide"]);
const CANON = { valider1: "valider-1", valider2: "valider-2", "marchés": "marches" };
const MAX_CAPTURE = 4096;
const HELP =
  "Campagne PARI — commandes :\n" +
  "/start\n" +
  "/capture  (markdown DANS le meme message, OU photo + caption /capture)\n" +
  "/bankroll 50000  (pot global, une fois)\n" +
  "/budget 3000 800  (plafond jour + mise FORCEE ticket sur)\n" +
  "/combos 3  ou  /combos 3:3:2:2\n" +
  "/marches  (hint du jour apres /valider-1 ; alias /marchés, option mono)\n" +
  "/valider-1\n" +
  "/valider-2  (lot pending + token L-XXX, anti-cannibal)\n" +
  "/approve L-XXX  (fige le lot pending)\n" +
  "/data  /data N  /data ledger  /data diag\n" +
  "/radar  /pack  /match ID\n" +
  "/status  /status ledger  /status doctor\n" +
  "/roi  /roi settle L-XXX\n" +
  "/stop";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("pari-listen", { status: 200 });
    }
    const secret = env.TELEGRAM_WEBHOOK_SECRET;
    if (secret) {
      const got = request.headers.get("X-Telegram-Bot-Api-Secret-Token") || "";
      if (got !== secret) return new Response("forbidden", { status: 403 });
    }
    let update;
    try {
      update = await request.json();
    } catch {
      return jsonOk({ ok: false, action: "ignore", reason: "bad_json" });
    }
    const parsed = parseUpdate(update, env.TELEGRAM_CHAT_ID);
    if (parsed.action === "ignore") return jsonOk(parsed);
    if (parsed.action === "reply" || parsed.action === "local") {
      await tgSend(env, parsed.chat_id, parsed.reply);
      return jsonOk(parsed);
    }
    await tgSend(env, parsed.chat_id, "Recu `" + parsed.cmd + "` — siege en cours (~1 min).");
    const dispatched = await ghDispatch(env, parsed);
    if (!dispatched.ok) {
      await tgSend(env, parsed.chat_id, "Dispatch GitHub echoue : " + dispatched.error);
    }
    return jsonOk({ ...parsed, dispatched: dispatched.ok });
  },
};

export function parseUpdate(update, allowedChatId) {
  const msg = (update && (update.message || update.edited_message)) || {};
  const chat = msg.chat || {};
  const text = msg.text || msg.caption || "";
  const chatId = String(chat.id || "");
  const allowed = String(allowedChatId || "");
  if (!chatId) {
    return { ok: false, action: "ignore", reason: "empty" };
  }
  if (!String(text).trim()) {
    if (photoFileId(msg)) {
      return {
        ok: false, action: "reply", reason: "capture_empty", chat_id: chatId,
        reply: "Photo recu sans commande. Envoie la photo AVEC caption /capture.",
      };
    }
    return { ok: false, action: "ignore", reason: "empty" };
  }
  if (!allowed || chatId !== allowed) {
    return { ok: false, action: "ignore", reason: "foreign_chat" };
  }
  const { name, extra } = headCmd(text);
  if (!name) {
    return {
      ok: false, action: "reply", reason: "not_a_command", chat_id: chatId,
      reply: "Commande inconnue. /help pour la liste.",
    };
  }
  if (LOCAL.has(name)) {
    return { ok: true, action: "local", cmd: "/help", chat_id: chatId, reply: HELP };
  }
  const canon = CANON[name] || name;
  if (!KNOWN.has(canon) && !KNOWN.has(name)) {
    return {
      ok: false, action: "reply", reason: "unknown", chat_id: chatId,
      reply: "Commande inconnue : /" + name + ". /help pour la liste.",
    };
  }
  if (canon === "capture") {
    const fileId = photoFileId(msg);
    if (!String(extra).trim() && !fileId) {
      return {
        ok: false, action: "reply", reason: "capture_empty", chat_id: chatId,
        reply: "Colle le tableau markdown Winner Bet DANS le meme message, sous /capture — ou envoie une PHOTO avec caption /capture. Plafond markdown 4096 caracteres.",
      };
    }
    if (!fileId && byteLen(extra) > MAX_CAPTURE) {
      return {
        ok: false, action: "reply", reason: "capture_too_long", chat_id: chatId,
        reply: "Capture trop longue (limite Telegram 4096). Envoie une photo avec caption /capture.",
      };
    }
    return {
      ok: true, action: "dispatch", cmd: "/capture",
      capture_text: fileId ? null : extra,
      capture_file_id: fileId,
      chat_id: chatId, update_id: update.update_id, message_id: msg.message_id,
    };
  }
  let cmd = "/" + canon;
  if (String(extra).trim() && (canon === "budget" || canon === "combos" || canon === "bankroll" || canon === "surticket" || canon === "data" || canon === "status" || canon === "roi" || canon === "radar" || canon === "pack" || canon === "match" || canon === "marches" || canon === "approve")) {
    cmd = cmd + " " + String(extra).split("\n")[0].trim();
  }
  return {
    ok: true, action: "dispatch", cmd, capture_text: null,
    chat_id: chatId, update_id: update.update_id, message_id: msg.message_id,
  };
}

function photoFileId(msg) {
  const photos = msg.photo || [];
  if (photos.length) {
    let best = photos[0];
    for (const p of photos) {
      const a = p.file_size || 0;
      const b = best.file_size || 0;
      if (a >= b) best = p;
    }
    if (best && best.file_id) return best.file_id;
  }
  const doc = msg.document || {};
  const mime = String(doc.mime_type || "").toLowerCase();
  const name = String(doc.file_name || "").toLowerCase();
  if (doc.file_id && (mime.indexOf("image/") === 0 || /\.(png|jpe?g|webp)$/.test(name))) {
    return doc.file_id;
  }
  return null;
}

function headCmd(text) {
  const raw = String(text || "").trim();
  if (!raw.startsWith("/")) return { name: null, extra: raw };
  const nl = raw.indexOf("\n");
  const first = nl === -1 ? raw : raw.slice(0, nl);
  const rest = nl === -1 ? "" : raw.slice(nl + 1).trim();
  const bits = first.split(/\s+/);
  let name = bits[0].slice(1);
  if (name.includes("@")) name = name.split("@")[0];
  name = name.toLowerCase();
  const arg0 = bits.slice(1).join(" ").trim();
  const extra = [arg0, rest].filter(Boolean).join("\n");
  return { name, extra };
}

function byteLen(s) {
  return new TextEncoder().encode(String(s)).length;
}

function jsonOk(obj) {
  return new Response(JSON.stringify(obj), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

async function tgSend(env, chatId, text) {
  const token = env.TELEGRAM_BOT_TOKEN;
  if (!token || !chatId || !text) return;
  const url = "https://api.telegram.org/bot" + token + "/sendMessage";
  await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text: String(text).slice(0, 3800) }),
  }).catch(() => {});
}

async function ghDispatch(env, parsed) {
  const token = env.GITHUB_DISPATCH_TOKEN;
  const owner = env.GH_OWNER;
  const repo = env.GH_REPO;
  const workflow = env.GH_WORKFLOW || "pari_listen.yml";
  const ref = env.GH_REF || "pari-forge-perturabo-xs4c";
  if (!token || !owner || !repo) {
    return { ok: false, error: "GITHUB_DISPATCH_TOKEN / GH_OWNER / GH_REPO absents" };
  }
  const url = "https://api.github.com/repos/" + owner + "/" + repo +
    "/actions/workflows/" + workflow + "/dispatches";
  const body = {
    ref,
    inputs: {
      cmd: parsed.cmd,
      capture_text: parsed.capture_text || "",
      capture_file_id: parsed.capture_file_id || "",
    },
  };
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "authorization": "Bearer " + token,
      "accept": "application/vnd.github+json",
      "content-type": "application/json",
      "user-agent": "pari-listen-worker",
      "x-github-api-version": "2022-11-28",
    },
    body: JSON.stringify(body),
  });
  if (res.status === 204) return { ok: true };
  const t = await res.text();
  return { ok: false, error: "HTTP " + res.status + " " + t.slice(0, 200) };
}
