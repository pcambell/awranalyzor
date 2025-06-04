import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { store } from './store';
import Layout from './components/Layout';
import Home from './pages/Home';
import Upload from './pages/Upload';
import Results from './pages/Results';
import ParseProgressPage from './pages/ParseProgress';
import History from './pages/History';
import './App.css';

// 应用主题配置 - KISS原则：保持简单
const themeConfig = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
    wireframe: false,
  },
  components: {
    Layout: {
      headerBg: '#001529',
      headerColor: '#ffffff',
      siderBg: '#001529',
    },
    Menu: {
      darkItemBg: '#001529',
      darkItemColor: '#ffffff',
      darkItemHoverBg: '#1890ff',
      darkItemSelectedBg: '#1890ff',
    },
  },
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        <Router>
          <Layout>
            <Routes>
              {/* 主要路由 */}
              <Route path="/" element={<Home />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/results/:id" element={<Results />} />
              <Route path="/parse-progress/:taskId" element={<ParseProgressPage />} />
              <Route path="/history" element={<History />} />
              
              {/* 重定向和错误处理 */}
              <Route path="*" element={<Home />} />
            </Routes>
          </Layout>
        </Router>
      </ConfigProvider>
    </Provider>
  );
};

export default App;
