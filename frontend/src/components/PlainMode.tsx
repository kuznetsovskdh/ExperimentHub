import * as React from "react";
import { Switch } from "@/components/ui/switch";

/**
 * Режим «Объяснять просто».
 *
 * Включён по умолчанию: интерфейс должен быть понятен человеку, который
 * открыл его впервые, а не тому, кто уже знает статистику. Кто знает —
 * выключит переключатель и получит точные формулировки.
 *
 * Выбор запоминается: заново объяснять свой уровень при каждом визите обидно.
 */
const PlainModeContext = React.createContext<{
  plain: boolean;
  setPlain: (v: boolean) => void;
}>({ plain: true, setPlain: () => {} });

const STORAGE_KEY = "eh-plain-mode";

export function PlainModeProvider({ children }: { children: React.ReactNode }) {
  const [plain, setPlainState] = React.useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === null ? true : stored === "1";
    } catch {
      return true;
    }
  });

  const setPlain = React.useCallback((v: boolean) => {
    setPlainState(v);
    try {
      localStorage.setItem(STORAGE_KEY, v ? "1" : "0");
    } catch {
      /* приватный режим — просто не запоминаем */
    }
  }, []);

  return (
    <PlainModeContext.Provider value={{ plain, setPlain }}>
      {children}
    </PlainModeContext.Provider>
  );
}

export const usePlainMode = () => React.useContext(PlainModeContext);

export function PlainModeToggle({ className }: { className?: string }) {
  const { plain, setPlain } = usePlainMode();
  const id = React.useId();

  return (
    <div className={className}>
      <label
        htmlFor={id}
        className="flex cursor-pointer select-none items-center gap-2.5"
      >
        <Switch id={id} checked={plain} onCheckedChange={setPlain} />
        <span className="text-[13px] text-muted transition-colors hover:text-ink">
          Объяснять просто
        </span>
      </label>
    </div>
  );
}
