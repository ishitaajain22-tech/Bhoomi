import { NavLink } from "react-router-dom";
import "./TopNav.css";

export default function TopNav() {
  return (
    <nav className="topnav">
      <div className="topnav__links">
        <NavLink to="/" className="topnav__link" end>Dashboard</NavLink>
        <NavLink to="/methodology" className="topnav__link">Methodology</NavLink>
      </div>
      <span className="topnav__tag">Bhoomi · ISRO Hackathon 2025 · Real Satellite Data</span>
    </nav>
  );
}
