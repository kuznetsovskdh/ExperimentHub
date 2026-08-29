import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { PlainModeProvider } from "@/components/PlainMode";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <PlainModeProvider>
        {/* delayDuration небольшой: подсказки здесь — основной способ понять
            интерфейс, ждать их полсекунды на каждом термине утомительно. */}
        <TooltipProvider delayDuration={150} skipDelayDuration={300}>
          <App />
        </TooltipProvider>
      </PlainModeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
