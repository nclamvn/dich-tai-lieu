export default function Loading() {
  return (
    <div className="p-6 space-y-6">
      <div className="h-8 w-48 skeleton" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 skeleton" />
        ))}
      </div>
      <div className="h-64 skeleton" />
    </div>
  );
}
