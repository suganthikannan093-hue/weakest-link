---
mode: agent
description: What to pack and the one item to buy for a venue, using the Weakest Link graph over Relate MCP
tools: ['weakest-link-mybag', 'weakest-link-catalog']
---
Follow [the pack-my-bag skill](../../agent/skills/pack-my-bag/SKILL.md) and
[the system rules](../../agent/prompts/system.md).

My laptop and bag: ${input:bag:laptop id and bag item ids, e.g. mba-m2; adp-apple-av-a1621, chg-apple-70w}

Venue email, page or product spec:
${input:text:paste the venue's AV email or a product spec page}
