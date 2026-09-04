import { PlaybookPageClient } from "@/components/PlaybookPageClient";

interface PlaybookPageProps {
  params: Promise<{ id: string }>;
}

export default async function PlaybookPage({ params }: PlaybookPageProps) {
  const { id } = await params;
  return <PlaybookPageClient key={id} jobId={id} />;
}
