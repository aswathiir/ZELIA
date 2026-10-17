import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CaseDetail from './pages/CaseDetail';
import CallInProgress from './pages/CallInProgress';
import Results from './pages/Results';
import ActiveCalls from './pages/ActiveCalls';
import Schemes from './pages/Schemes';
import History from './pages/History';
import Settings from './pages/Settings';
import AdminDocuments from './pages/AdminDocuments';

// Citizen-facing side
import CitizenLogin from './pages/CitizenLogin';
import CitizenPortal from './pages/CitizenPortal';
import CitizenRegister from './pages/CitizenRegister';
import EligibilityForm from './pages/EligibilityForm';
import CitizenDocuments from './pages/CitizenDocuments';

import { LanguageProvider } from './context/LanguageContext';
import { DocumentProvider } from './context/DocumentStore';

function App() {
  return (
    <LanguageProvider>
      <DocumentProvider>
        <BrowserRouter>
          <Routes>
            {/* ── OFFICER ROUTES ─────────────────────────── */}
            <Route path="/login" element={<Login />} />

            <Route path="/" element={<Layout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="case/:hashId" element={<CaseDetail />} />
              <Route path="call-in-progress" element={<CallInProgress />} />
              <Route path="results" element={<Results />} />
              <Route path="active-calls" element={<ActiveCalls />} />
              <Route path="history" element={<History />} />
              <Route path="schemes" element={<Schemes />} />
              <Route path="settings" element={<Settings />} />
              <Route path="documents" element={<AdminDocuments />} />
              <Route path="reports" element={
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', fontSize: 18, fontWeight: 600 }}>
                  Report Generation — Coming Soon
                </div>
              } />
            </Route>

            {/* ── CITIZEN ROUTES ─────────────────────────── */}
            <Route path="/citizen-login" element={<CitizenLogin />} />
            <Route path="/citizen-register" element={<CitizenRegister />} />
            <Route path="/citizen" element={<CitizenPortal />} />
            <Route path="/citizen/documents" element={<CitizenDocuments />} />
            <Route path="/eligibility" element={<EligibilityForm />} />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </DocumentProvider>
    </LanguageProvider>
  );
}

export default App;
