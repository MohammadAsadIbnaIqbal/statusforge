import { TokenAction } from "@/components/TokenAction";

export default async function UnsubscribePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return (
    <TokenAction
      endpoint={"/subscribers/unsubscribe/" + encodeURIComponent(token)}
      title="Unsubscribe"
      loadingText="Processing your request..."
      fallbackSuccess="Successfully unsubscribed."
    />
  );
}
