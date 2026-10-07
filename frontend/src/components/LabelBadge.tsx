type Props = { label: string };

export default function LabelBadge({ label }: Props) {
  const normalized = label.toLowerCase();
  let cls = "gray";
  if (normalized.includes("highly recommended")) cls = "green";
  else if (normalized.includes("recommended")) cls = "blue";
  else if (normalized.includes("review") || normalized.includes("borderline")) cls = "orange";
  else if (normalized.includes("weak") || normalized.includes("not recommended") || normalized.includes("manual")) cls = "red";
  return <span className={`badge ${cls}`}>{label}</span>;
}
