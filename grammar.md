
# Grammar

Below is the grammar for the credit policy language. At the highest level, the policy is a chain of rulesets. Chain is defined as a simple list of rulesets and is executed in sequence of definition. A chain is a logical grouping of rules. Ruleset is a list of rules. 

Rule is the fundamental building block and actual unit of logic. It represents a single node in the graph. This is the place where conditions can be defined and a decision can be be made. The decision can be one of continuing to execute or fail the execution. 

```
POLICY = 
  "id", "name",
  "chains" : { CHAIN },
  "terminal_nodes" : { TERMINAL_NODE };

CHAIN =
  "id", "name",
  "rulesets" : { RULESET };

RULESET =
  "id", "name",
  "rules" : { RULE };

RULE =
  "id", "name",
  [ "conditions" : { CONDITION } ],
  "action" : ACTION ;

CONDITION =
  "field",
  "operator" : OPERATOR,
  "value" ;

OPERATOR = "==" | "!=" | ">" | ">=" | "<" | "<=" | "REGEX_MATCH" ;

ACTION =
  [ "on_true"  : OUTCOME ],
  [ "on_false" : OUTCOME ];

OUTCOME =
  [ "decision" ],
  [ "reason" ],
  [ "next_rules" : { RULE_ID } ],
  [ "next_ruleset" ];

BRANCH =
  "name",
  "conditions" : { CONDITION },
  "next_rules" : { RULE_ID },
  "next_ruleset" ;

TERMINAL_NODE =
  "id",
  "decision" ;
```

