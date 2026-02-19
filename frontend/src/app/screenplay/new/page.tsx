"use client";

import Link from "next/link";
import { CreateWizard } from "@/components/screenplay/Wizard/CreateWizard";
import "@/styles/screenplay.css";

export default function NewScreenplayPage() {
  return (
    <div className="screenplay-page">
      <div className="screenplay-page-header">
        <Link href="/screenplay" className="screenplay-back-link">
          &larr; Back to Projects
        </Link>
        <h1>Create New Project</h1>
      </div>
      <CreateWizard />
    </div>
  );
}
