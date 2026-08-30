# Framing: an experiment that gave the wrong answer, and how it was caught

_Reproduce with `python ml/measure_framing.py`; raw numbers in `eval/framing.json`._

## The question

The 92.2% figure is measured on the dataset's tight hand crops, padded before
detection the way `ml/extract_landmarks.py` pads them. The live page sees
something quite different: a whole webcam frame, in which MediaPipe has to find
the hand itself among a face, a room and a background.

So: is 92.2% a true statement about an experiment and a misleading one about the
page a stranger opens?

## The first answer, which was wrong

Compositing each dataset crop into a mid-grey 640×480 frame and detecting there
gave this:

| framing | detected | accuracy on detected |
| --- | ---: | ---: |
| padded crop (as measured) | 99.6% | 99.4% |
| composited frame, hand 25% of height | 51.2% | 81.9% |
| composited frame, hand 40% of height | 56.0% | 73.1% |
| composited frame, hand 60% of height | 63.2% | 90.3% |

Read literally that says MediaPipe finds a hand in a realistic frame barely half
the time, and the model is far worse when it does. It would have gone into the
README as a serious limitation, in bold.

It is an artefact.

## The ablation

The giveaway is that accuracy does not fall monotonically with hand size — 40% of
frame height scores *worse* than 25% and 60%. A real size effect would not do
that. So the sweep was widened to cross background colour with hand size, which
is the variable that had been held fixed without justification:

| background | h=0.25 | h=0.40 | h=0.60 | h=0.80 |
| --- | ---: | ---: | ---: | ---: |
| **black** | 81.0% | 99.7% | 99.6% | 97.5% |
| **grey** | 51.2% | 56.0% | 63.2% | 69.5% |

Detection tracks the **background**, not the hand size. On black it holds at
97–100% for any hand larger than a quarter of the frame. On grey it never gets
above 70%.

The cause is the compositing itself. Pasting a crop onto a flat field leaves a
hard rectangular seam, and MediaPipe's palm detector does not cope with it. On a
black field the seam is invisible, because the crops' own backgrounds are dark.
No webcam produces a seam like that.

## What this experiment does and does not establish

**It does not measure webcam performance.** It measures a detector's sensitivity
to a synthetic edge. No number in the grey rows should be quoted as if a visitor
would experience it, and the original conclusion — "detection halves on a real
webcam" — has no support.

Two things it does establish, both from the black rows, where the composite is
not fighting an artificial seam:

- **A hand smaller than about a third of the frame is a problem.** Detection
  falls from 99.7% to 81.0% between 40% and 25% of frame height. That is a real
  effect, and it is the one piece of guidance a visitor can act on: fill the
  frame.
- **Framing costs about three points of accuracy by itself.** 96–97% in a full
  frame against 99.4% on the padded crop, on the same images with the same
  model. Small, but not nothing, and it is a floor rather than an estimate —
  these are images the shipped model trained on.

## What is still not measured

Real webcam performance, by anybody, on this model. That needs video of a person
signing to a camera, and there is none here; the honest position is to say so
rather than to substitute a synthetic proxy that has now twice proved to measure
something else. `README.md` says exactly this under **Honest limits**.

## Why this is written down

The first result was alarming, plausible and wrong, and it would have survived
into the README because it pointed the way a sceptical reading expects — the
demo being worse than the benchmark. The check that caught it was noticing that
the numbers were not monotonic in the variable being claimed, and then sweeping
the variable that had been held fixed by accident. That is worth more than the
result.
