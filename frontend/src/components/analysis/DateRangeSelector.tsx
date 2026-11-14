import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useFiltersStore } from "@/stores/filters.store";

const PRODUCTS = ["", "GCOV", "GUNW", "GOFF", "SME2"];

export function DateRangeSelector() {
  const { startDate, endDate, productType, setRange, setProductType } = useFiltersStore();

  return (
    <div className="grid grid-cols-2 gap-2">
      <label className="flex flex-col gap-1 text-xs text-muted">
        Desde
        <Input
          type="date"
          value={startDate}
          max={endDate}
          onChange={(event) => setRange(event.target.value, endDate)}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Hasta
        <Input
          type="date"
          value={endDate}
          min={startDate}
          onChange={(event) => setRange(startDate, event.target.value)}
        />
      </label>
      <label className="col-span-2 flex flex-col gap-1 text-xs text-muted">
        Producto
        <Select value={productType} onChange={(event) => setProductType(event.target.value)}>
          {PRODUCTS.map((product) => (
            <option key={product || "all"} value={product}>
              {product || "Todos"}
            </option>
          ))}
        </Select>
      </label>
    </div>
  );
}
