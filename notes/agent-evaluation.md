# Can the meturgaman agent teach? An evaluation with evidence

Written 2026-08-06. Every claim in this file points at a transcript or a
verification report in `notes/evaluation/`, and every verification was run by
a separate agent instructed to fetch each cited passage and try to break it.
Nothing below rests on my impression of an answer I did not check.

## What was tested

The six questions from the project brief, put to the agent twice: once before
any change ("baseline", the agent spec as it stood this morning) and once
after the spec was rewritten around teaching and the commentary-traversal
commands were added ("rebuilt"). Twelve transcripts, nine independent
verification reports. Questions 1 through 5 were asked verbatim. Question 6
("find me something I would not have thought to look for") needs a subject to
point at, so it carried one context sentence naming the asker as a contracts
and business law professor; both rounds used the same sentence.

Judged against the brief's four criteria: are the citations real and fetched;
does the answer have a shape; did it find anything; where is it thin.

## The headline findings

**It teaches, and that was already mostly true before the rewrite.** The
baseline answers were far better than the brief feared. They fetched real
texts, named editions and licences, built arguments with structure, and found
sources worth finding. The instrument the last session built appears to be
the reason: an agent that must fetch produces answers that survive checking.

**The failures were specific, and the rewrite addressed them measurably.**
Verification of the baseline found three kinds of error, none of them an
invented text: a census generated from memory, a tool result misdescribed,
and references copied imprecisely. The rewritten spec turned each failure
into a standing rule, and the second round showed real improvement on all
three, without eliminating the third entirely.

**Residual weakness, stated plainly: counting and anchoring.** Even the
rebuilt agent said "seven glosses" where the fetched work carries twelve
glossed halakhot, and placed one gloss at 4:2 that both editions anchor at
4:3. It no longer invents and it no longer dresses guesses as tool output,
but small census and location slips survive, so a number or an anchor in its
answers still deserves a check when it matters.

## Per-question judgement

### Question 1, lending at interest (baseline and rebuilt both strong)

Baseline: ten of ten citation-bound claims verified, including the Rema's
gloss at Yoreh De'ah 160:1 word for word and the isqa structure at 177:2
([verification-q1.md](evaluation/verification-q1.md)). Shape: Torah, Mishnah,
Shulchan Arukh, then the business-loan question answered directly with the
heter iska explained from the fetched isqa texts. Found: the Warburg debate
on whether corporations need a heter iska at all, which answers the question
the asker did not know to ask. Thin: heter iska practice described without a
fetched instrument, which the rebuilt answer then flagged about itself,
unprompted.

Rebuilt: adds Rav Nachman's governing principle at Bava Metzia 63b:10 (every
premium for waiting is forbidden), the Sifrei's dispute on the foreigner
clause reported as a dispute, and an explicit paragraph marking which part is
historical characterization rather than fetched text. All three additions
spot-checked against fetched text and confirmed.

### Question 2, the sugya at Bava Metzia 75b (the walkthrough holds up)

Baseline: all fifteen segment-level content claims verified against the
fetched amud, and all eight verse citations
([verification-q2.md](evaluation/verification-q2.md)). The structural reading
(coin to labor to time to speech, then the pivot to creditor ethics, then the
aggadic close) is the agent's own and it is the kind of reading a teacher
gives. One real failure: the claim that "the `sugya` command confirms the
unit is the whole amud" is false; the tool reports five passages, two
crossing the page. The interpretation was defensible, the attribution of it
to the tool was not.

Rebuilt: the false tool claim is gone. In its place the agent noticed the
English edition holds no text at 75b:14, checked the gap against three
witnesses, and reported the hadran correctly. The structural teaching stayed
as strong ([rebuilt-q2-bava-metzia-75b.md](evaluation/rebuilt-q2-bava-metzia-75b.md)).

### Question 3, Rambam and Ravad on repentance (the failure case, then the fix)

Baseline: philologically excellent and arithmetically unreliable. Every
quoted Hebrew phrase was real and verbatim, but the census that framed the
whole answer ("nine places") was generated from memory and wrong: three
hassagot missing, one located a halakhah off
([verification-q3.md](evaluation/verification-q3.md)). This is the clearest
evidence in the whole evaluation that fetched quotations and remembered
overviews can coexist in one answer, which is exactly why the brief demanded
verification rather than a read-through.

Rebuilt: the chapter-level census is now exactly right (2, 3, 4, 5, 6, 8, 10
glossed; 1, 7, 9 empty), it covers the hassagot the baseline missed (3:5,
3:9, 8:4), and it caught a genuine translation error in the Glazer edition at
10:6 that only a side-by-side fetch could catch
([verification-rebuilt-q3.md](evaluation/verification-rebuilt-q3.md)). Two
slips remain: "seven glosses" is right only as a chapter count, and the
shor/shod gloss is placed at 4:2 when both fetched editions anchor it at 4:3.
Better, not yet clean.

### Question 4, asmakhta (clean twice, more honest the second time)

Baseline: six of six claims verified, down to the character
([verification-q4.md](evaluation/verification-q4.md)). Two shadings: a
licence misreported from memory, and one side of an amoraic dispute at
Sanhedrin 24b presented as the explanation.

Rebuilt: reports the Bava Batra 168a dispute as a dispute, says "I did not
fetch that page" about the one thing it did not fetch, surfaces that the
rishonim disagree about what an exegetical asmakhta even is, and closes by
overriding a romanization flag with its reasoning stated. Spot checks of its
new citations (Moed Katan 3a:9, Bava Batra 168a:14, Mishneh Torah Sales 11:2)
all confirmed against fetched text.

### Question 5, limited liability (the hardest question, and the sharpest fix)

Baseline: an honest and well-shaped answer whose verification found real
errors: the guarantor rule cited one mishnah off, the two apoteke formulas of
Choshen Mishpat 117:1 swapped (a substantive error a halakhist would catch),
and a quotation taken from a stale search-index snapshot of Peninei Halakhah
that the live text no longer contains
([verification-q5.md](evaluation/verification-q5.md)).

Rebuilt: six of six verified, the formulas now correctly distributed and the
Sma's definition quoted from the Sma, the Warburg chapter paraphrased rather
than quoted because its licence is unknown, and the stale-snippet source
dropped entirely ([verification-rebuilt-q5.md](evaluation/verification-rebuilt-q5.md)).
Residual blemishes: the author's name garbled once ("Warhaftig" for Warburg)
and one American-law example imported into a sentence about halakhah.

### Question 6, surprise me (where the agent earns the word teacher)

Baseline: situmta at Bava Metzia 74a, custom as a generator of contract
formalities, verified nine for nine including the details a model writing
from memory typically fumbles (Rav Pappi, not Rav Pappa)
([verification-q6.md](evaluation/verification-q6.md)). For a contracts
scholar this is a genuinely excellent find.

Rebuilt: the same find, deepened into a line of authority (Maharam through
the Rosh to the Chatam Sofer, against R. Akiva Eiger), with the live dispute
stated as live. Verification: five verified, two misattributed, and both
misattributions share one shape, treating a siman heading or a later
authority's citation as the location of the text itself. The handshake
examples sit at Choshen Mishpat 201:2, not 201:1, and the Rosh's holding sits
at 13:21 of the edition fetched, while the agent repeated the traditional
"13:20" it inherited from the Chatam Sofer's own citation
([verification-rebuilt-q6.md](evaluation/verification-rebuilt-q6.md)). The
agent's own closing caveat had flagged exactly that risk, which is the
discipline working even where the reference failed.

## What this supports saying, and what it does not

Supported: the agent answers real questions about Jewish law and thought with
fetched, edition-named sources; it explains structure rather than listing; it
reports disagreement as disagreement; it finds material the asker did not
name; its quotations survive hostile verification at a very high rate; and
after the rewrite it marks the boundary between evidence and its own reading.

Not supported: treating its counts, anchors, and location citations as
reliable without a check. The residual error class is narrow and it is real.
Three of twelve transcripts carried a wrong count or a reference off by one
unit even in the improved round.

Not tested: aggadah-first questions, liturgy, Yiddish sources, multi-session
study, and anything requiring texts absent from Sefaria. Nothing here says
how it does on those.

## Method notes, for whoever repeats this

- Twelve answer transcripts and nine verification reports are in
  `notes/evaluation/`, verbatim, with the em dashes and hedges the agents
  actually produced. Editing them would have destroyed the evidence.
- Verification agents received the transcript and the CLI, plus explicit
  instruction to trust nothing from memory. Their reports name the fetched
  evidence for each verdict, so their own claims are checkable too.
- The verifiers themselves made one instructive error: both Q3 verifications
  agree with each other against the transcripts, but where a verifier's claim
  mattered (the 4:3 anchor), a second independent run was used to confirm it
  before this file treated it as fact.
