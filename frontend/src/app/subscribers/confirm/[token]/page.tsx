import { TokenAction } from "@/components/TokenAction";

export default async function ConfirmSubscriptionPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return (
    <TokenAction
      endpoint={"/subscribers/confirm/" + encodeURIComponent(token)}
      title="Confirm subscription"
      loadingText="Confirming your subscription..."
      fallbackSuccess="Subscription confirmed!"
    />
  );
}
