import { Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Layout } from "@/components/Layout";
import Home from "@/pages/Home";
import Guide from "@/pages/Guide";
import Experiments from "@/pages/Experiments";
import ExperimentDetail from "@/pages/ExperimentDetail";
import NewExperiment from "@/pages/NewExperiment";
import Tools from "@/pages/Tools";
import GlossaryPage from "@/pages/Glossary";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return null;
}

export default function App() {
  return (
    <Layout>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/guide" element={<Guide />} />
        <Route path="/experiments" element={<Experiments />} />
        <Route path="/experiments/:id" element={<ExperimentDetail />} />
        <Route path="/new" element={<NewExperiment />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/glossary" element={<GlossaryPage />} />
      </Routes>
    </Layout>
  );
}
