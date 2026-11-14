import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/explorer", label: "Explorador" },
  { to: "/analysis/new", label: "Análisis" },
  { to: "/insights", label: "Insights" },
  { to: "/data-sources", label: "Fuentes de datos" },
];

export function Navigation() {
  return (
    <nav className="flex flex-col gap-1">
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            `rounded-md px-3 py-2 text-sm transition-colors ${
              isActive
                ? "bg-surface-border/80 font-medium text-accent"
                : "text-slate-300 hover:bg-surface-border/50"
            }`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
