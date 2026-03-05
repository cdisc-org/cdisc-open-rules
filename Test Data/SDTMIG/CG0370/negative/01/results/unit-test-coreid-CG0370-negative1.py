{
  "CO": [
    {
      "executionStatus": "success",
      "dataset": "co.xpt",
      "domain": "CO",
      "variables": [
        "IDVAR",
        "RDOMAIN",
        "USUBJID"
      ],
      "message": "IDVAR does not represent a variable present in the dataset identified in RDOMAIN",
      "errors": [
        {
          "value": {
            "USUBJID": "S001",
            "IDVAR": "LBSEK",
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
        "RDOMAIN",
        "USUBJID"
      ],
      "message": "IDVAR does not represent a variable present in the dataset identified in RDOMAIN",
      "errors": [
        {
          "value": {
            "USUBJID": "S001",
            "IDVAR": "LBSEK",
            "RDOMAIN": "LB"
          },
          "dataset": "relrec.xpt",
          "row": 1,
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
        "RDOMAIN",
        "USUBJID"
      ],
      "message": "IDVAR does not represent a variable present in the dataset identified in RDOMAIN",
      "errors": [
        {
          "value": {
            "USUBJID": "S001",
            "IDVAR": "LBSEK",
            "RDOMAIN": "LB"
          },
          "dataset": "supplb.xpt",
          "row": 1,
          "USUBJID": "S001"
        }
      ]
    }
  ],
  "LB": [
    {
      "executionStatus": "skipped",
      "dataset": "lb.xpt",
      "domain": "LB",
      "variables": [],
      "message": "Rule skipped - doesn't apply to domain for rule id=CDISC.SDTMIG.CG0370, dataset=LB",
      "errors": []
    }
  ]
}