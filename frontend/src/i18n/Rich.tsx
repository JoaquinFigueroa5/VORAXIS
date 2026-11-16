import { Fragment } from "react";

/**
 * Dictionary prose with the little markup it needs: `**bold**` becomes <strong>
 * and `` `code` `` a mono figure (`.num`). Nothing else is interpreted, so a
 * translation can never inject HTML.
 */
export function Rich({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <span key={index} className="num">
              {part.slice(1, -1)}
            </span>
          );
        }
        return <Fragment key={index}>{part}</Fragment>;
      })}
    </>
  );
}
