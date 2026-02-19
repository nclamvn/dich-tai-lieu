export default function Loading() {
  return (
    <div className="p-6 space-y-4">
      <div className="h-8 w-48 skeleton" />
      <div className="h-10 skeleton" />
      <div className="space-y-2">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="h-12 skeleton" />
        ))}
      </div>
    </div>
  );
}
