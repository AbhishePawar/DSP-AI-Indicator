import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'

import AppLayout from './layouts/AppLayout'
import AuthLayout from './layouts/AuthLayout'
import MarketingLayout from './layouts/MarketingLayout'

// Core app pages
import Dashboard from './pages/Dashboard'
import CompanyAnalysis from './pages/CompanyAnalysis'
import SecurityCompare from './pages/SecurityCompare'
import Portfolio from './pages/Portfolio'
import ResearchHub from './pages/ResearchHub'
import InstitutionalResearch from './pages/InstitutionalResearch'
import ResearchCanvas from './pages/ResearchCanvas'
import ResearchIntelligence from './pages/ResearchIntelligence'
import CompanyDirectory from './pages/CompanyDirectory'
import Advisor from './pages/Advisor'
import AICopilot from './pages/AICopilot'
import ControlCenter from './pages/ControlCenter'
import AdminPanel from './pages/AdminPanel'
import Diagnostics from './pages/Diagnostics'
import ClientProfile from './pages/ClientProfile'
import Coupons from './pages/Coupons'

// Auth pages
import Login from './pages/auth/Login'
import Signup from './pages/auth/Signup'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import VerifyEmail from './pages/auth/VerifyEmail'

// Marketing pages
import LandingPage from './pages/LandingPage'
import About from './pages/marketing/About'
import Contact from './pages/marketing/Contact'
import FAQ from './pages/marketing/FAQ'
import Pricing from './pages/marketing/Pricing'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Marketing */}
          <Route element={<MarketingLayout />}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/faq" element={<FAQ />} />
            <Route path="/pricing" element={<Pricing />} />
          </Route>

          {/* Auth */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
          </Route>

          {/* App */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analysis" element={<CompanyAnalysis />} />
            <Route path="/compare" element={<SecurityCompare />} />
            <Route path="/analysis/compare" element={<SecurityCompare />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/research" element={<ResearchHub />} />
            <Route path="/research/institutional" element={<InstitutionalResearch />} />
            <Route path="/research/canvas" element={<ResearchCanvas />} />
            <Route path="/research/intelligence" element={<ResearchIntelligence />} />
            <Route path="/companies" element={<CompanyDirectory />} />
            <Route path="/advisor" element={<Advisor />} />
            <Route path="/copilot" element={<AICopilot />} />
            <Route path="/control-center" element={<ControlCenter />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/diagnostics" element={<Diagnostics />} />
            <Route path="/profile" element={<ClientProfile />} />
            <Route path="/coupons" element={<Coupons />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
