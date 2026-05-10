import Link from "next/link";

const links = [
  { href: "/", label: "Overview" },
  { href: "/ranking", label: "Ranking" },
  { href: "/risk", label: "Risk" },
  { href: "/audit", label: "Audit" },
];

export function NavigationBar() {
  return (
    <nav style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          style={{
            padding: "10px 16px",
            borderRadius: 999,
            textDecoration: "none",
            color: "#e2e8f0",
            background: "rgba(30,41,59,0.72)",
            border: "1px solid rgba(148,163,184,0.16)",
          }}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
