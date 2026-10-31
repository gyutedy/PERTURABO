/**
 * PARI LISTEN — Cloudflare Worker (webhook Telegram)
 * Relais uniquement : allowlist chat_id, parse commande, ACK, dispatch GitHub.
 * Miroir de parse.py. Zero calcul, zero Dixon-Coles.
 *
 * Secrets wrangler (jamais dans git) :
 *   TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_WEBHOOK_SECRET, GITHUB_DISPATCH_TOKEN
 * Vars wrangler.toml :
 *   GH_OWNER, GH_REPO, GH_WORKFLOW, GH_REF
 */

const KNOWN = new Set([
  "start", "capture", "bankroll", "budget", "surticket", "combos",
  "valider-1", "valider-2", "valider1", "valider2",
  "data", "status", "roi", "stop",
]);
const LOCAL = new Set(["help", "aide"]);
const CANON = { valider1: "valider-1", valider2: "valider-2" };
const MAX_CAPTURE = 4096;
const HELP =
  "Campagne PARI — commandes :\n" +
  "/start\n" +
  "/capture  (colle le tableau markdown DANS le meme message)\n" +
  "/bankroll 50000  (pot global, une fois)\n" +
  "/budget 3000 800  (plafond jour + mise FORCEE ticket sur)\n" +
  "/combos 3  ou  /combos 3:3:2:2\n" +
  "/valider-1\n" +
  "/valider-2\n" +
  "/data  /status  /roi  /stop";

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
  if (!chatId || !String(text).trim()) {
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
    if (!String(extra).trim()) {
      return {
        ok: false, action: "reply", reason: "capture_empty", chat_id: chatId,
        reply: "Colle le tableau markdown Winner Bet DANS le meme message, sous /capture. png/pdf plus tard. Plafond 4096 caracteres.",
      };
    }
    if (byteLen(extra) > MAX_CAPTURE) {
      return {
        ok: false, action: "reply", reason: "capture_too_long", chat_id: chatId,
        reply: "Capture trop longue (limite Telegram 4096). Decoupe, png plus tard.",
      };
    }
    return {
      ok: true, action: "dispatch", cmd: "/capture", capture_text: extra,
      chat_id: chatId, update_id: update.update_id, message_id: msg.message_id,
    };
  }
  let cmd = "/" + canon;
  if (String(extra).trim() && (canon === "budget" || canon === "combos" || canon === "bankroll" || canon === "surticket")) {
    cmd = cmd + " " + String(extra).split("\n")[0].trim();
  }
  return {
    ok: true, action: "dispatch", cmd, capture_text: null,
    chat_id: chatId, update_id: update.update_id, message_id: msg.message_id,
  };
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
