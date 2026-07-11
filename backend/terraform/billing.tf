# resource "google_billing_budget" "project_budget" {
#   billing_account = data.google_billing_account.account.id
#   display_name    = "2-Week Project Budget"

#   amount {
#     specified_amount {
#       currency_code = "USD"
#       units         = "300" # Free credits
#     }
#   }

#   # Scope to your specific project
#   budget_filter {
#     projects               = ["projects/${data.google_project.project.number}"]
#     credit_types_treatment = "INCLUDE_ALL_CREDITS"

#     custom_period {
#       start_date {
#         year  = 2025
#         month = 12
#         day   = 2
#       }
#       end_date {
#         year  = 2025
#         month = 12
#         day   = 16
#       }
#     }
#   }

#   threshold_rules {
#     threshold_percent = 0.33 # $100
#   }

#   threshold_rules {
#     threshold_percent = 0.67 # $200
#   }

#   threshold_rules {
#     threshold_percent = 0.90 # $270
#   }

#   threshold_rules {
#     threshold_percent = 1.0 # $300 (100%)
#   }

#   threshold_rules {
#     threshold_percent = 1.0
#     spend_basis       = "FORECASTED_SPEND"
#   }
# }
