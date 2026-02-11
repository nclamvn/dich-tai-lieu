export default function Loading() {
  return (
    <div className="p-6 space-y-4">
      <div className="h-8 w-48 skeleton" />
      <div className="space-y-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-16 skeleton" />
        ))}
      </div>
    </div>
  );
}
