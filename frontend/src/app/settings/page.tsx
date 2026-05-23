import { redirect } from "next/navigation";

/** Settings moved to Environment — keep old URL working */
export default function SettingsRedirect() {
  redirect("/environment");
}
