# Individual Reflection — Amine Kebichi
**CS7180 — Vibe Coding | GOALS Project**

---

Going into this project I honestly underestimated how much the tooling would change the way I work. I've built full-stack apps before, but I've never had an AI assistant embedded this deeply into the development loop — not just generating boilerplate, but actively catching bugs I would have shipped, managing GitHub issues from the terminal, and enforcing code quality on every file save through hooks. That shift took some getting used to.

The hardest part technically was the Prisma binary target problem. The app built fine in CI, the logs showed success, but every page returned a 500 in production. There was nothing in the error output that pointed to the cause — I had to dig into Vercel's function logs, cross-reference the Prisma docs, and eventually figure out that the binary compiled on Ubuntu doesn't run on Vercel's Amazon Linux Lambda. Adding two words to `schema.prisma` fixed it. That's the kind of bug you only find once, but it cost a few hours I didn't budget for. I've added it to my mental checklist for any future Prisma-on-Vercel project.

The position group mapping bug was a different kind of frustrating — it was a data bug, not a code bug. The feature engineering notebook had quietly labelled every outfield player as a midfielder for months. It didn't surface until the match detail page rendered and every team showed nothing but midfielders and goalkeepers. The fix itself was two lines in the export script, but discovering it required manually inspecting the parquet schema and cross-referencing known players. It reminded me that data validation belongs in the pipeline, not as an afterthought at the UI layer.

What genuinely surprised me was how much the agent workflow changed my relationship to security. Before this class, security was something I thought about after writing code. Having the `security-reviewer` agent run against every PR meant I was reading security findings in real time, while the code was fresh in my head. It flagged the path traversal in the seed script and the unvalidated season parameter in the API — both things I'd have called low-priority before understanding the actual attack vectors. Now I think about allowlists and path resolution as part of writing the feature, not a review step afterward.

If I could redo one thing, I'd set up the CI pipeline before writing a single line of application code. I added it late in Sprint 2, which meant a lot of manual testing early on that the pipeline would have caught automatically. Setting up lint, typecheck, and Vitest on day one forces you to write testable code from the start — it's much harder to retrofit.

The collaboration with Nicholas worked well because we stayed on separate branches with clear ownership. The one friction point was the position group issue — a notebook output that affected both the ML pipeline and the seeding script. Clearer integration contracts between the notebook outputs and the export scripts would have saved time.

Overall I'm proud of what we shipped. A live, deployed app with real predictions, real player data, and a CI/CD pipeline that keeps it honest — that's more than I expected to have at the start of the semester.
