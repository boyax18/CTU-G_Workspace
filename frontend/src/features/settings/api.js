import { getJSON, postJSON } from "../../api/client";

export const getSettings = () => getJSON("/api/v1/auth/settings/");

export const updateSettings = (settings) => postJSON("/api/v1/auth/settings/", settings);
