import { getJSON } from "../../api/client";

export const getClearance = () => getJSON("/api/v1/clearance/");