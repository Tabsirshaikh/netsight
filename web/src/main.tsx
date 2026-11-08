import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import AppV2 from './AppV2';
import './styles.css';

// v1 (original site) at /, v2 (restructured after the team review) at /v2
const Root = window.location.pathname.replace(/\/+$/, '').endsWith('/v2') ? AppV2 : App;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
