import { PlaybookPageClient } from "@/components/PlaybookPageClient";

interface PlaybookPageProps {
  params: { id: string };
}

export default function PlaybookPage({ params }: PlaybookPageProps) {
  return <PlaybookPageClient jobId={params.id} />;
}
