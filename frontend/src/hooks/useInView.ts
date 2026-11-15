import { useCallback, useEffect, useState } from "react";

/**
 * True the first time the element enters the viewport. One shot: once seen, it
 * stays seen, so a 10-second refetch never replays the entrance.
 *
 * The ref is a callback, which lets one element be both a measurement target and
 * something else (the statement also needs its own ref for the word-highlight kit).
 * Without IntersectionObserver the caller gets true immediately, so nothing stays
 * hidden when the browser does not support it.
 */
export function useInView<T extends Element>(rootMargin = "0px 0px -10% 0px") {
  const [node, setNode] = useState<T | null>(null);
  const [inView, setInView] = useState(false);
  const ref = useCallback((value: T | null) => setNode(value), []);

  useEffect(() => {
    if (!node || inView) return;

    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { rootMargin, threshold: 0.05 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [node, inView, rootMargin]);

  return { ref, inView };
}
