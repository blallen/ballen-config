<!-- ballen-config:self-review-result:v1 -->
```json
{
  "contract_version": "v1",
  "result_id": "d3e83dc\u00647a739a8\u00302ec7b63\u006680c5a02\u006550b496c\u0034559e10b\u0039502dbf7\u003888c308c\u0032",
  "created_at": "2026-07-30T20:00:00Z",
  "result_digest": "beacc22\u0065f3035b5\u0036696d6e3\u00380ee447e\u0066fb95679\u0063779f44c\u00663282250\u00624311d70\u0064",
  "repository_identity": {
    "state": "complete",
    "vcs": "jujutsu",
    "value": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "code": null
  },
  "scope": {
    "status": "resolved",
    "source": "jujutsu",
    "request": {
      "mode": "explicit",
      "selector": "review-foundation-types..review-foundation-self-review"
    },
    "comparison": {
      "kind": "jujutsu-explicit-range",
      "base_identities": [
        {
          "state": "resolved",
          "value": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        }
      ],
      "target_identity": {
        "state": "resolved",
        "value": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
      },
      "resolved_selector": "review-foundation-types..review-foundation-self-review"
    },
    "target_change_id": "cccccccccccccccccccccccccccccccc",
    "scope_identity": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "changed_paths": [
      ".gitignore",
      "assistants/shared/skills/conduct-self-review/SKILL.md",
      "assistants/shared/skills/review-project-standards/SKILL.md",
      "src/review.py",
      "tests/assistants/test_review_contracts.py"
    ],
    "diff_digest": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    "coverage": {
      "entries": "complete",
      "textual_diff": "complete",
      "overall": "complete",
      "unreviewable_paths": []
    }
  },
  "standards_inventory_ref": "4444444444444444444444444444444444444444444444444444444444444444",
  "reviewers": [
    {
      "contract_version": "v1",
      "reviewer": "review-project-standards",
      "scope_identity": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "standards_inventory_ref": "4444444444444444444444444444444444444444444444444444444444444444",
      "applicability": "applicable",
      "outcome": "completed",
      "coverage": {
        "scope": "complete",
        "inputs": "complete",
        "checks": [
          {
            "check": "repository-standards",
            "required": true,
            "selected_scope": "changed-files",
            "completion": "completed"
          }
        ]
      },
      "findings": [
        {
          "finding_id": "5555555555555555555555555555555555555555555555555555555555555555",
          "category": "documentation",
          "severity": "advisory",
          "source_severity": "Nit",
          "path": "src/review.py",
          "location": {
            "start_line": 18,
            "end_line": 18
          },
          "rule": "DOCSTRING-SUMMARY",
          "evidence": "The public function uses an expanded docstring for a single-sentence contract.",
          "remediation": "Use a one-line summary for this simple public function.",
          "contributors": [
            "review-project-standards"
          ]
        }
      ],
      "skips": [],
      "commands": [],
      "summary": {
        "counts": {
          "blocker": 0,
          "actionable": 0,
          "advisory": 1
        },
        "verdict": "advisories"
      }
    },
    {
      "contract_version": "v1",
      "reviewer": "review-project-quality",
      "scope_identity": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "standards_inventory_ref": "4444444444444444444444444444444444444444444444444444444444444444",
      "applicability": "applicable",
      "outcome": "completed",
      "coverage": {
        "scope": "complete",
        "inputs": "complete",
        "checks": [
          {
            "check": "configured-quality-gate",
            "required": true,
            "selected_scope": "changed-python-files",
            "completion": "completed"
          }
        ]
      },
      "findings": [
        {
          "finding_id": "6666666666666666666666666666666666666666666666666666666666666666",
          "category": "documentation",
          "severity": "actionable",
          "source_severity": "D200",
          "path": "src/review.py",
          "location": {
            "start_line": 18,
            "end_line": 18
          },
          "rule": "DOCSTRING-SUMMARY",
          "evidence": "The public function uses an expanded docstring for a single-sentence contract.",
          "remediation": "Collapse the docstring to a single summary line.",
          "contributors": [
            "review-project-quality"
          ]
        }
      ],
      "skips": [],
      "commands": [
        {
          "invocation_id": "7777777777777777777777777777777777777777777777777777777777777777",
          "provenance": "pyproject.toml:[tool.ruff]",
          "selected_scope": "changed-python-files",
          "completion": "completed",
          "exit_status": 1,
          "evidence": "One in-scope docstring diagnostic was reported.",
          "unrun_reason": null
        }
      ],
      "summary": {
        "counts": {
          "blocker": 0,
          "actionable": 1,
          "advisory": 0
        },
        "verdict": "needs_attention"
      }
    },
    {
      "contract_version": "v1",
      "reviewer": "review-project-tests",
      "scope_identity": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "standards_inventory_ref": "4444444444444444444444444444444444444444444444444444444444444444",
      "applicability": "applicable",
      "outcome": "completed",
      "coverage": {
        "scope": "complete",
        "inputs": "complete",
        "checks": [
          {
            "check": "test-quality",
            "required": true,
            "selected_scope": "changed-tests",
            "completion": "completed"
          }
        ]
      },
      "findings": [],
      "skips": [],
      "commands": [],
      "summary": {
        "counts": {
          "blocker": 0,
          "actionable": 0,
          "advisory": 0
        },
        "verdict": "clean"
      }
    },
    {
      "contract_version": "v1",
      "reviewer": "review-python-types",
      "scope_identity": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "standards_inventory_ref": "4444444444444444444444444444444444444444444444444444444444444444",
      "applicability": "applicable",
      "outcome": "completed",
      "coverage": {
        "scope": "complete",
        "inputs": "complete",
        "checks": [
          {
            "check": "configured-type-checker",
            "required": true,
            "selected_scope": "full",
            "completion": "completed"
          }
        ]
      },
      "findings": [],
      "skips": [],
      "commands": [
        {
          "invocation_id": "8888888888888888888888888888888888888888888888888888888888888888",
          "provenance": "pyproject.toml:[tool.mypy]",
          "selected_scope": "full",
          "completion": "completed",
          "exit_status": 0,
          "evidence": "The configured type checker completed without diagnostics.",
          "unrun_reason": null
        }
      ],
      "summary": {
        "counts": {
          "blocker": 0,
          "actionable": 0,
          "advisory": 0
        },
        "verdict": "clean"
      }
    }
  ],
  "findings": [
    {
      "finding_id": "5555555555555555555555555555555555555555555555555555555555555555",
      "category": "documentation",
      "severity": "actionable",
      "source_severity": "D200",
      "path": "src/review.py",
      "location": {
        "start_line": 18,
        "end_line": 18
      },
      "rule": "DOCSTRING-SUMMARY",
      "evidence": "The public function uses an expanded docstring for a single-sentence contract.",
      "remediation": "Collapse the docstring to a single summary line.",
      "contributors": [
        "review-project-quality",
        "review-project-standards"
      ]
    }
  ],
  "commands": [
    {
      "invocation_id": "7777777777777777777777777777777777777777777777777777777777777777",
      "provenance": "pyproject.toml:[tool.ruff]",
      "selected_scope": "changed-python-files",
      "completion": "completed",
      "exit_status": 1,
      "evidence": "One in-scope docstring diagnostic was reported.",
      "unrun_reason": null
    },
    {
      "invocation_id": "8888888888888888888888888888888888888888888888888888888888888888",
      "provenance": "pyproject.toml:[tool.mypy]",
      "selected_scope": "full",
      "completion": "completed",
      "exit_status": 0,
      "evidence": "The configured type checker completed without diagnostics.",
      "unrun_reason": null
    }
  ],
  "skips": [],
  "diagnostics": [],
  "summary": {
    "counts": {
      "blocker": 0,
      "actionable": 1,
      "advisory": 0
    },
    "verdict": "needs_attention"
  }
}
```

## Human summary

The review needs attention: one actionable finding and no blockers or
advisories.
