resource "google_bigquery_dataset_iam_member" "rls_20261009_eeef7cdd" {
  project    = var.project_id
  dataset_id = "rls_f_seo_dashboard"
  table_id   = "cmdb_website_owners"
  role       = "roles/bigquery.dataViewer"
  member     = "user:p@pg.com"
}
