import React from 'react';
import { Provider } from 'react-redux';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import { store } from './store';
import Layout from './components/Layout';
import Home from './pages/Home';
import Upload from './pages/Upload';
import Results from './pages/Results';
import History from './pages/History';
import './App.css';

const { defaultAlgorithm, darkAlgorithm } = theme;

function App() {
  // 可以从localStorage或state获取主题设置
  const isDarkMode = false; // 暂时固定为false，后续可以改为动态

  return (
    <Provider store={store}>
      <ConfigProvider
        theme={{
          algorithm: isDarkMode ? darkAlgorithm : defaultAlgorithm,
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 6,
            colorBgContainer: '#ffffff',
          },
        }}
      >
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/results" element={<Results />} />
              <Route path="/results/:id" element={<Results />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </Layout>
        </Router>
      </ConfigProvider>
    </Provider>
  );
}

export default App;
