import { getJSON } from "../../api/client";

export const getAnnouncements = () => getJSON("/api/v1/announcements/");
