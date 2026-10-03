import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

const ToastContext = createContext<(message: string) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<{ id: number; text: string }[]>([]);
  const push = useCallback((text: string) => {
    const id = Date.now();
    setMessages((current) => [...current, { id, text }]);
    window.setTimeout(() => setMessages((current) => current.filter((item) => item.id !== id)), 2400);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-wrap" aria-live="polite">
        {messages.map((item) => (
          <div className="toast" key={item.id}>{item.text}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
