# Reflection
 
I built a multi-agent system that allocates hospital beds and nurses across four departments, day by day, with clinical priority, fairness and efficiency as its main criteria. Before running the agents, I fixed the evaluation metrics, generated the datasets from explicit stochastic processes for patient arrivals and discharges, and built a deterministic audit that checks every decision independently of any LLM. Claude Code wrote most of the code. I supervised it throughout, with the support of an LLM advisor (Claude). The agents did well: no constraint violations in any run, the optimum on the bed metric, slightly better than the greedy baseline on nurses, and 1,015 of 1,049 explanation claims correct. What the project taught me is that making the agents perform well was the easier part. Establishing that they perform well was the harder one.
 
Three problems recurred.
 
First, the CHECKER was less reliable than I expected. It was designed to review each day's allocation and the ALLOCATOR's explanation. On the allocation, it largely repeated what the deterministic audit already did, at a much higher cost. On the explanations, where it could have added something the code cannot, it caught only 4 of the 19 errors confirmed in my review, and 3 of its 7 disputes were wrong because it reasoned on the previous day's allocation. It tended to read the ALLOCATOR's statements the way the ALLOCATOR meant them, instead of recomputing the quantities. An LLM judging another LLM is not independent just because it is a different agent (Zheng et al.).
 
Second, some development errors passed every test. A test silently rewrote a frozen file with identical bytes. Figures with hidden series passed their tests and were caught only when the images were opened. Some evaluation scripts wrote by default into folders holding frozen evidence. A test checks only the property it was written for: passing it does not make a system correct, and a run that completes is not a run whose outputs are right.
 
Third, agents sometimes stated verifications they had not done. On day 12 the ALLOCATOR wrote that a wrong figure "matches the queue records", in a message only the transcript records. Claude Code's error log, which it writes itself, attributes 30 of the 54 detected development errors to its own checks. That is not an independent measure of its ability to find them. Plausible verification statements create an illusion of reliability that only an independent check can confirm or dismiss.
 
None of this argues for checking everything by hand. Most of the verification in this project was automated: the audit, the tests and guards, the hash checks, and the byte-identical recomputation of every reported number. Manual work was needed for one thing only, a reference for the explanation claims of one run, and its main value was showing where the automated checker fell short. The lesson is that verification must be independent of the system it checks, not that it must be manual.
 
Next time I would:
- prefer deterministic checks to LLM judges wherever the property can be computed, and give LLM reviewers the tools to recompute what they check;
- treat every agent report, including the coding agent's, as a claim to be verified with a different tool;
- fix falsification thresholds before running the experiments, which I did not do here;
- turn recurring errors into tests and guards rather than extra instructions. In this project, 17 corrections became tests and only 2 became rules in `CLAUDE.md`.

In high-stakes settings such as healthcare, finance or aviation, I would trust an agent not because its reasoning sounds right or because it agrees with another agent, but because its outputs pass checks it does not control.
