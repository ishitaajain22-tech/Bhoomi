import { BrowserRouter, Routes, Route } from "react-router-dom";
import TopNav from "./components/TopNav/TopNav";
import Dashboard from "./pages/Dashboard";
import FieldDetailPage from "./pages/FieldDetailPage";
import MethodologyPage from "./pages/MethodologyPage";
import "./styles/tokens.css";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display:"flex", flexDirection:"column", height:"100vh", overflow:"hidden" }}>
        <TopNav />
        <div style={{ flex:1, overflow:"auto" }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/fields/:fieldId" element={<FieldDetailPage />} />
            <Route path="/methodology" element={<MethodologyPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
