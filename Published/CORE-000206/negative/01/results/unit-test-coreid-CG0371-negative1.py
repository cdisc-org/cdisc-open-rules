{
  "CO": [
    {
      "executionStatus": "success",
      "dataset": "co.xpt",
      "domain": "CO",
      "variables": [
        "IDVAR",
        "IDVARVAL",
        "RDOMAIN",
        "USUBJID"
      ],
      "message": "IDVARVAL does not equal a value of variable=IDVAR in domain=RDOMAIN",
      "errors": [
        {
          "value": {
            "USUBJID": "S001",
            "IDVARVAL": "20",
            "IDVAR": "LBGRPID",
            "RDOMAIN": "LB"
          },
          "dataset": "co.xpt",
          "row": 1,
          "USUBJID": "S001",
          "SEQ": 1
        }
      ]
    }
  ],
  "RELREC": [
    {
      "executionStatus": "success",
      "dataset": "relrec.xpt",
      "domain": "RELREC",
      "variables": [
        "IDVAR",
        "IDVARVAL",
        "RDOMAIN",
        "USUBJID"
      ],
      "message": "IDVARVAL does not equal a value of variable=IDVAR in domain=RDOMAIN",
      "errors": [
        {
          "value": {
            "USUBJID": "S001",
            "IDVARVAL": "320",
            "IDVAR": "LBSEQ",
            "RDOMAIN": "LB"
          },
          "dataset": "relrec.xpt",
          "row": 1,
          "USUBJID": "S001"
        },
        {
          "value": {
            "USUBJID": "S001",
            "IDVARVAL": "321",
            "IDVAR": "AESEQ",
            "RDOMAIN": "AE"
          },
          "dataset": "relrec.xpt",
          "row": 2,
          "USUBJID": "S001"
        }
      ]
    }
  ],
  "SUPPLB": [
    {
      "executionStatus": "success",
      "dataset": "supplb.xpt",
      "domain": "SUPPLB",
      "variables": [
        "IDVAR",
        "IDVARVAL",
        "RDOMAIN",
        "USUBJID"
      ],
      "message": "IDVARVAL does not equal a value of variable=IDVAR in domain=RDOMAIN",
      "errors": [
        {
          "value": {
            "USUBJID": "S001",
            "IDVARVAL": "320",
            "IDVAR": "LBSEQ",
            "RDOMAIN": "LB"
          },
          "dataset": "supplb.xpt",
          "row": 1,
          "USUBJID": "S001"
        }
      ]
    }
  ],
  "AE": [
    {
      "executionStatus": "skipped",
      "dataset": "ae.xpt",
      "domain": "AE",
      "variables": [],
      "message": "Rule skipped - doesn't apply to domain for rule id=CORE-000206, dataset=AE",
      "errors": []
    }
  ],
  "LB": [
    {
      "executionStatus": "skipped",
      "dataset": "lb.xpt",
      "domain": "LB",
      "variables": [],
      "message": "Rule skipped - doesn't apply to domain for rule id=CORE-000206, dataset=LB",
      "errors": []
    }
  ]
}