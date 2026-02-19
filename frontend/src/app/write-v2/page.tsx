"use client";

import { useLocale } from "@/lib/i18n";
import { BookCreateForm, BookListV2 } from "@/components/book-writer-v2";

export default function WriteV2Page() {
  const { t } = useLocale();

  return (
    <div className="space-y-8">
      <div>
        <h1>{t.writeV2.title}</h1>
        <p className="mt-2" style={{ color: "var(--fg-secondary)" }}>
          {t.writeV2.subtitle}
        </p>
      </div>

      <BookCreateForm />
      <BookListV2 />
    </div>
  );
}
