# Ticket Submission

There are cases where you may be trying to write a rule and you find that operators or processes are not yet available to allow you to write your rule. In other cases, you may find that the rule can be written but it is not working as expected or the CORE engine is returning a strange error in the results. The following steps will help you decide where to report the problem and how to create a ticket.

## Is it an engine issue?

Report the issue to the **CORE engine repository** ([cdisc-org/cdisc-rules-engine](https://github.com/cdisc-org/cdisc-rules-engine/issues)) if:

- The engine returns an error, crashes, or produces unexpected results for a rule that appears to be written correctly
- An operator behaves differently than its documentation describes
- An operator or process you need to write your rule does not exist yet

If the problem is with a rule's own logic or content rather than the engine, it is not an engine bug. Do not file it in the engine repository. Instead, open an issue in the rule repository for that standard:

| Standard | Where to report rule issues |
| --- | --- |
| SDTM, ADaM, FDA Business Rules | [verisianHQ/core-contributor](https://github.com/verisianHQ/core-contributor/issues) |
| SEND, TIG, USDM | [cdisc-org/cdisc-open-rules](https://github.com/cdisc-org/cdisc-open-rules/issues) |

## Submitting a ticket

1. Before submitting a ticket, check the [FAQ](./faq.md) to make sure your question has not already been answered.
2. Search the existing issues to see whether the problem has already been reported. For engine problems, look in the [engine issues](https://github.com/cdisc-org/cdisc-rules-engine/issues). For rule problems, look in the rule repository from the table above. If the issue already exists, add a comment with your example instead of opening a duplicate.
3. Create a GitHub issue in the correct repository and choose the template that fits:
   - **Rule-Blocking Bug** (engine repository): the engine is not behaving as expected
   - **Rule-Blocking Enhancement** (engine repository): the engine needs an operator or process that does not exist yet
   - **New Rule or Existing Rule Bug** (rule repository): a rule has a logic issue, or a new rule needs to be created

   If you do not have a GitHub account, follow the prompts to create one.
4. Follow the instructions in the issue template and include as much information as possible to help with triage and development.

## Volunteering

If you would like to author rules as a volunteer, please visit https://www.cdisc.org/volunteer/form