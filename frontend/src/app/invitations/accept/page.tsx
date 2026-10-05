import { AcceptInvitation } from "./AcceptInvitation";

export default async function AcceptInvitationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string | string[] }>;
}) {
  const { token } = await searchParams;
  const value = Array.isArray(token) ? token[0] : token;
  return <AcceptInvitation token={value || null} />;
}
