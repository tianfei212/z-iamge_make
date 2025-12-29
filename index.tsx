
import ReactDOM from 'react-dom/client';
import App from './App';
import { ConfigManagement } from './pages/ConfigManagement';
import { StrictMode, useEffect, useState } from 'react';
import { ToastContainer } from './components/Toast';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
function Router() {
  const [path, setPath] = useState(location.pathname);
  useEffect(() => {
    const onPop = () => setPath(location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  if (path === '/config-management') {
    return <ConfigManagement />;
  }
  return <App />;
}

root.render(
  <StrictMode>
    <>
      <ToastContainer />
      <Router />
    </>
  </StrictMode>
);
