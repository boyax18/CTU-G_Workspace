import { getJSON, postJSON } from "../../api/client";

export const getHelpArticles = (category = "") =>
  getJSON(category ? `/api/v1/help/articles/?category=${encodeURIComponent(category)}` : "/api/v1/help/articles/");

export const submitHelpRequest = (subject, message) =>
  postJSON("/api/v1/help/contact/", { subject, message });
