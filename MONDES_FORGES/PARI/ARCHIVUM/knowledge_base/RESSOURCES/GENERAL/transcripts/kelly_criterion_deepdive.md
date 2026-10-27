# Transcription brute — kelly_criterion_deepdive — TO_CONFIRM

- **ID vidéo** : TO_CONFIRM
- **Chaîne** : Luck by Numbers
- **URL** : https://www.youtube.com/watch?v=TO_CONFIRM
- **Date de publication (upload YouTube)** : TO_CONFIRM
- **Date de récupération de la transcription** : 2026-10-27
- **Catégorie** : GENERAL
- **Statut** : brut
- **Crouse frâches vérifiées** : N
- **Notes de fraîcheur** : (ex: "stats de forme = saison 24-25 → probablement obsolète pour la saison courante")

---

## Texte brut (repères minute si disponibles)

[min 00:00] Let's play a game. Imagine we flip a coin. If it's heads, I'll pay you 3 times your bet. If it's tails, you lose it all. You have $100 and an infinite number of rounds to play. How much will you bet each round?
The Kelly Criterion tells us the optimal amount to bet. In this case, it's 25% of your wealth – but why?
If you've searched for the Kelly Criterion on YouTube, you'd notice that most videos just explain the derivation and basic application, but almost no one dives deeper.
In this video, we're going beyond the basics. I'll take you deeper as we explore the Kelly Criterion iceberg.
Welcome to Luck by Numbers, where luck meets logic.
Let's start with the basics.
Imagine you're at the casino, and I offer you this deal: pay $1 to roll a 6-sided fair die. If you roll a 6, you gain $2 on top of your $1 bet. If you roll anything else, you lose it all. Would you take the bet?
The expected value is the winning probability times the gain, plus the losing probability times the loss, which gives us negative one-half. On average, you lose half of your bet each round, so the clear choice is not to play the game. You may get lucky the first few times, but in the long run, you donate all your money to the casino.
Now, let's change the rules. What if I made the deal even better? Imagine you gain 10 times your bet if you roll a 6. Would you play now?
The expected value becomes 5 over 6. On average, you gain five-sixths of your bet each round, so now you should play the game.
This is the easy part. The hard part is, how should you play this game in the smartest way possible?
If you're playing a game with a positive expected value, why not bet everything every round and get rich as fast as possible? Seems logical, right?
Suppose you have $100, and you can play this game an infinite number of times. For the first round, we're lucky and turned $100 into 1,100. we bet everything again and turn it into 12.1 thousand. We put everything in again and again and get more than a million dollars in the 4th round! However, we lose in the 5th round and go bankrupt. This shows us something critical: even in a game with a positive expected value, betting recklessly can lead to ruin. Clearly, betting 100% of your wealth every round is not the smartest strategy.
If betting 100% of your wealth is too risky, what happens if we bet less? Let's try 50%.
I ran 100 simulations. The green lines show the wins, and the red lines show the losses. The yellow line represents the median outcome – the typical player.
Look at what happens. The yellow line drops to zero quickly, meaning the average player still goes bankrupt. Even at 50%, betting too much eventually wipes out your wealth.
What if we bet only 10% this time? I ran the same simulation again. Now, the yellow line goes up! The average player profits over time.
The optimal percentage must be somewhere between 10% and 50%.
Let's start by defining what exactly we are trying to maximise. Suppose there is a game with a winning probability p and a losing probability q, which equals 1-p. If we win, we gain a fraction g of our bet; if we lose, we lose a fraction l of our bet. What fraction f of our wealth do we bet to maximise our return?
Let's say we have a total wealth of S. In each round, we bet a fraction f of it. If we win, our profit is g times fS. Our wealth becomes fS + fgS, or simply (1+fg)S. In other words, our wealth is multiplied by 1+fg. Similarly, if we lose, our wealth is multiplied by 1-fl.
After playing n rounds, we expect to win np rounds and lose nq rounds.
Therefore, our total return is: 1 plus fg to the power np times 1 minus fl to the power nq.
But if we look at the geometric average return in one round, we can take the n-th root, removing the n.
Let's plot the graph of r against f to see how r changes with f. The maximum average return is at the top of this curve, where the slope is zero. Therefore, we can take the derivative, set it equal to zero, and then solve for f.
Calculating the derivative right away seems tedious because we have exponents. Let's take the logarithm on both sides first.
Then, we can calculate the derivative of log r and set it equal to zero. After some simplifications, we get this formula:
f equals p over l minus q over g.
This is the Kelly Criterion! It tells us how much of our wealth we should bet each round to maximise our average return in the long run.
Returning to our game, we plug in p equals 1 over 6, q equals 5 over 6, g equals 10, l equals 1, and get f equals 1 over 6. So, the optimal strategy is to bet one-sixth of our wealth every round.
Now, most videos about the Kelly Criterion stop here, they explain the formula and give examples, but let's dive deeper!
Suppose we flip a fair coin, and you are betting on heads. Situation A: If the game has 2-to-1 odds, the Kelly Criterion tells you to bet 25% of your wealth. Situation B: If the game has 5-to-1 odds, it tells you to bet 40%.
Now, suppose that these bets occur in sequence. I offer you 2-to-1 odds, and you bet 25% of your wealth. Then, I say, oh wait, actually, I'll give you 5-to-1 odds on the additional amount you bet if you choose to bet more. We call this situation C. Should you place an additional bet, and if so, how much?
Let f be the additional fraction of your wealth that you bet. We compute the following table showing the two bets. For the first bet of 0.25S, you gain 0.5S if you win and lose 0.25S if you lose. For the second bet of fS, you gain 5fS if you win and lose fS if you lose.
Your total gain is 0.5S plus 5fs, and your total loss is 0.25S plus fS. Plug these numbers into our equation for the average return and solve for the optimal fraction f just like before. We get f equals 0.225.
Therefore, your total bet is 0.25 plus 0.225, which is 47.5%, greater than the 40% in situation B.
Wait WHAT? Even though situation C has worse odds than situation B – because part of your bet is at 2-to-1 odds – the Kelly Criterion tells you to bet more in total. How does that make sense?
This is the Proebsting's Paradox!
One way to think about it is that the 25% you put in is already gone! It's not your money anymore! When the 5-to-1 odds come up, you should bet an additional 40% of your current wealth. You have 75% of your money left in your pocket, and 40% times 75% is… 30%? It still doesn't match the 22.5% number we obtained earlier. What's happening?
Remember, we are asking how much fraction of our wealth we should bet. Most people focus on the "fraction" part of the problem statement but miss the "wealth" part.
Warren Buffet has a wealth of 146 billion US dollars. It doesn't mean he has 146 billion in cash. For example, he could have 46 billion US dollars in cash, and then a stock portfolio valued at 100 billion US dollars. This is our everyday definition of wealth – cash plus net assets. Surprisingly, this is precisely how we define wealth in the Kelly Criterion too.
Suppose you can buy Contract A for $1. It pays you $3 in the future with 50% probability and nothing otherwise. According to the Kelly Criterion, you buy 25 units of A. Now, your wealth shifts from $100 in cash to $75 in cash plus $25 in assets, which is the market value of 25 units of A.
Now, Contract B appears on the market, also for $1. It pays you $6 instead of $3. Contract A gives 2-to-1 odds, while Contract B gives 5-to-1 odds. Naturally, everyone would buy Contract B!
But what if the price of Contract A drops to $0.8? Will people switch back to A? How about $0.3? Let's determine the drop in price of Contract A such that both contracts are equally worthy to the buyers.
Let d be the price drop, so the new price is 1 minus d. Initially, A offers a loss equal to the $1 cost, or a gain of $3 minus the $1 cost, which is $2. Now, our loss is 1 minus d, and our gain is 3 minus the new cost, which gives 2 plus d.
For both contracts to be equally worthy, Contract A should give 5-to-1 odds as well! So, the ratio between our gain and our loss should be 5. We get d equals 0.5. The new price of A is $0.5, dropping by half.
Therefore, the market value of the 25 units of A in our inventory should drop by half too. Our new wealth is $75 plus $12.5, equalling $87.5. Now, let's reconcile this paradox.
Situation C tells you to put 22.5% of your original $100, equalling $22.5. Situation B tells you to put 40% of your new wealth at $87.5, minus $12.5 of non-cash, equalling $22.5 as well! We have reconciled the results!
In fact, for any initial odds b_1 to 1 and follow-up odds b_2 to 1, we have the following formula for the additional bet. Try to prove that both methods show the same result!
Let's take the Kelly Criterion to the next level.
So far, we've been working with discrete outcomes. But what happens if the returns are continuously distributed?
Initially, we have this formula for the average return r. If we have three outcomes t1, t2, and t3, with probabilities p1, p2, and p3, we can extend this equation as follows.
If we have n outcomes, we can further extend the equation like this.
To find the optimal fraction f, we do the same thing. We take the logarithm on both sides first to bring the exponents down.
To extend this formula for log r from n outcomes to an infinite number of continuously distributed outcomes, we change the summation into an integral from A to B, where we assume all outcomes are contained in the interval from A to B. Then, we change p_i into the probability distribution function p(t), t_i into t, and times dt at the end.
What bet in this world has a continuous distribution of outcomes? One example is a stock. We can use this framework to determine how much money we should put into a stock!
Consider a stock with an average return mu equal to 0.1 and a standard deviation sigma equal to 0.5. The returns follow a normal distribution.
For any probability distribution, the area under the curve must be 1. This yellow line shows the average return of 0.1, perfectly splitting the curve into two halves.
Note that the return on a stock cannot go lower than -100%. In the worst case, you lose everything but not more. So, we cut the curve off at t equals -1.
When we truncate the curve, the area under the curve is no longer 1. The red area is calculated by the integral from negative infinity to -1 of the curve. We label that as N(-1).
The remaining area is then 1 minus N(-1).
To restore the total area to 1, we rescale the curve by dividing the probability density function by 1 minus N(-1). This gives us a new probability distribution function, shown here as the green curve q(t).
Going back to our equation for log r. To calculate the derivative, we only need to differentiate the log 1 plus ft part, giving us t over 1 plus ft.
We plot the log r curve and find that the maximum return is somewhere in the middle from 0 to 1. This is where the derivative goes to zero.
When the average return mu increases, the optimal fraction increases as well. This makes sense because the higher the average return, the better the odds of making more money.
When the standard deviation sigma decreases, the stock is less volatile. Because the average return is positive, having a lower volatility means we have less chance of going into negative returns. Therefore, f approaches one.
There's still so much we haven't covered in this video. For example, how do we actually solve for the optimal fraction f in practice?
And what's the connection between the Kelly Criterion and the Sharpe Ratio – a key metric in trading? In fact, we can approximate the Kelly fraction as the Sharpe Ratio divided by the standard deviation.
Another concept is the fractional Kelly Criterion. Some people may be risk-averse and only want to bet half of the optimal fraction. How does this change the risk and reward?
If you are curious about these topics, please let me know in the comments below so I can make a follow-up video!
You're watching Luck by Numbers. If you enjoyed this video, please like, subscribe, and share your thoughts below!