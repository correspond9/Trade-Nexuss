import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './components/core/ErrorBoundary';
import { AppProvider } from './contexts/AppContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/core/ProtectedRoute';
import Layout from './components/core/Layout';

// Lazy loaded pages for code splitting
const Trade = React.lazy(() => import('./pages/Trade'));
const Users = React.lazy(() => import('./pages/Users'));
const Userwise = React.lazy(() => import('./pages/Userwise'));
const Payouts = React.lazy(() => import('./pages/Payouts'));
const Ledger = React.lazy(() => import('./pages/Ledger'));
const PandL = React.lazy(() => import('./pages/PandL'));
const PositionsMIS = React.lazy(() => import('./pages/PositionsMIS'));
const PositionsNormal = React.lazy(() => import('./pages/PositionsNormal'));
const PositionsUserwise = React.lazy(() => import('./pages/PositionsUserwise'));
const Login = React.lazy(() => import('./pages/Login'));
const Profile = React.lazy(() => import('./pages/Profile'));
const SuperAdmin = React.lazy(() => import('./pages/SuperAdmin'));
const Options = React.lazy(() => import('./pages/OPTIONS'));
const Watchlist = React.lazy(() => import('./pages/WATCHLIST'));
const StraddlyEmbed = React.lazy(() => import('./pages/StraddlyEmbed'));
const Commodities = React.lazy(() => import('./pages/Commodities'));

// Wrapper component for Watchlist to provide required props
const WatchlistWrapper = () => {
  const handleOpenOrderModal = () => {
    // Placeholder function - can be implemented later
    console.log('Order modal requested from watchlist');
  };
  
  return <Watchlist handleOpenOrderModal={handleOpenOrderModal} />;
};

// Wrapper to pass URL param to StraddlyEmbed
const StraddlyRoute = () => {
  const { pageKey } = useParams();
  return <StraddlyEmbed pageKey={pageKey} />;
};

// Loading component
const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-r-2 border-indigo-600 border-t-transparent border-l-transparent"></div>
  </div>
);

const ScrollToTop = () => {
  const location = useLocation();
  React.useEffect(() => {
    try {
      window.scrollTo({ top: 0, behavior: 'auto' });
    } catch {
      window.scrollTo(0, 0);
    }
  }, [location.pathname, location.search, location.hash]);
  return null;
};

const HomeRedirect = () => {
  const { user } = useAuth();
  const role = user?.role;
  const isAdmin = role === 'ADMIN' || role === 'SUPER_ADMIN';
  return <Navigate to={isAdmin ? '/dashboard' : '/options'} replace />;
};

const App = () => {
  React.useEffect(() => {
    try {
      if ('scrollRestoration' in window.history) {
        window.history.scrollRestoration = 'manual';
      }
      window.scrollTo({ top: 0, behavior: 'auto' });
    } catch {
      try {
        window.scrollTo(0, 0);
      } catch {}
    }
  }, []);
  
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppProvider>
          <Router>
            <ScrollToTop />
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={
                <React.Suspense fallback={<LoadingSpinner />}>
                  <Login />
                </React.Suspense>
              } />
              
              {/* Specific routes first - to avoid conflicts */}
              <Route path="/users" element={<ProtectedRoute requiredRoles={['ADMIN', 'SUPER_ADMIN']}><Layout /></ProtectedRoute>}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Users />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/payouts" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Payouts />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/ledger" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Ledger />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/userwise" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Userwise />
                  </React.Suspense>
                } />
              </Route>
              
              {/* Protected routes */}
              <Route path="/options" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Options />
                  </React.Suspense>
                } />
              </Route>
              
              <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route index element={<HomeRedirect />} />
                <Route path="dashboard" element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <SuperAdmin />
                  </React.Suspense>
                } />
                <Route path="trade" element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Trade />
                  </React.Suspense>
                } />
                <Route path="commodities" element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <Commodities />
                  </React.Suspense>
                } />
              </Route>
              
              {/* Trade pages with proper nested routing */}
              <Route path="/trade/all-positions" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <PositionsMIS />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/trade/all-positions-normal" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <PositionsNormal />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/trade/all-positions-userwise" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <PositionsUserwise />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/trade/pandl" element={<Layout />}>
                <Route index element={
                  <React.Suspense fallback={<LoadingSpinner />}>
                    <PandL />
                  </React.Suspense>
                } />
              </Route>
              <Route path="/profile" element={
                <ProtectedRoute>
                  <Layout>
                    <React.Suspense fallback={<LoadingSpinner />}>
                      <Profile />
                    </React.Suspense>
                  </Layout>
                </ProtectedRoute>
              } />
              <Route path="/super-admin" element={
                <ProtectedRoute>
                  <Layout>
                    <React.Suspense fallback={<LoadingSpinner />}>
                      <SuperAdmin />
                    </React.Suspense>
                  </Layout>
                </ProtectedRoute>
              } />
              <Route path="/watchlist" element={
                <ProtectedRoute>
                  <Layout>
                    <React.Suspense fallback={<LoadingSpinner />}>
                      <WatchlistWrapper />
                    </React.Suspense>
                  </Layout>
                </ProtectedRoute>
              } />

                {/* Straddly static UI embeds */}
                <Route path="straddly">
                  <Route
                    path=":pageKey"
                    element={
                      <React.Suspense fallback={<LoadingSpinner />}>
                        <StraddlyRoute />
                      </React.Suspense>
                    }
                  />
                  {/* Named helpers for common pages */}
                  <Route
                    path="watchlist"
                    element={
                      <React.Suspense fallback={<LoadingSpinner />}>
                        <StraddlyEmbed pageKey="watchlist" />
                      </React.Suspense>
                    }
                  />
                  <Route
                    path="options"
                    element={
                      <React.Suspense fallback={<LoadingSpinner />}>
                        <StraddlyEmbed pageKey="options" />
                      </React.Suspense>
                    }
                  />
                  <Route
                    path="orders"
                    element={
                      <React.Suspense fallback={<LoadingSpinner />}>
                        <StraddlyEmbed pageKey="orders" />
                      </React.Suspense>
                    }
                  />
                  <Route
                    path="ledger"
                    element={
                      <React.Suspense fallback={<LoadingSpinner />}>
                        <StraddlyEmbed pageKey="ledger" />
                      </React.Suspense>
                    }
                  />
                  <Route
                    path="payouts"
                    element={
                      <React.Suspense fallback={<LoadingSpinner />}>
                        <StraddlyEmbed pageKey="payouts" />
                      </React.Suspense>
                    }
                  />
                </Route>
              
              {/* Catch all route - must be last */}
              {/* <Route path="*" element={<Navigate to="/dashboard" replace />} /> */}
            </Routes>
          </Router>
        </AppProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
