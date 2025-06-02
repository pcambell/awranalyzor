import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Layout as AntdLayout,
  Menu,
  Typography,
  Space,
  Breadcrumb,
  Button,
  Avatar,
  Dropdown,
  MenuProps,
} from 'antd';
import {
  HomeOutlined,
  UploadOutlined,
  BarChartOutlined,
  HistoryOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = AntdLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 菜单项
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/upload',
      icon: <UploadOutlined />,
      label: '文件上传',
    },
    {
      key: '/results',
      icon: <BarChartOutlined />,
      label: '解析结果',
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: '历史记录',
    },
  ];

  // 用户菜单
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ];

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  // 处理用户菜单点击
  const handleUserMenuClick = ({ key }: { key: string }) => {
    switch (key) {
      case 'logout':
        // 处理退出登录
        localStorage.removeItem('authToken');
        navigate('/login');
        break;
      default:
        console.log('User menu click:', key);
    }
  };

  // 面包屑映射
  const breadcrumbMap: { [key: string]: string } = {
    '/': '首页',
    '/upload': '文件上传',
    '/results': '解析结果',
    '/history': '历史记录',
  };

  // 生成面包屑
  const getBreadcrumbs = () => {
    const pathSnippets = location.pathname.split('/').filter(i => i);
    const breadcrumbItems = [
      {
        title: (
          <span>
            <HomeOutlined />
            <span>首页</span>
          </span>
        ),
      },
    ];

    pathSnippets.forEach((snippet, index) => {
      const url = `/${pathSnippets.slice(0, index + 1).join('/')}`;
      const isLast = index === pathSnippets.length - 1;
      
      if (breadcrumbMap[url]) {
        breadcrumbItems.push({
          title: isLast ? (
            <span>{breadcrumbMap[url]}</span>
          ) : (
            <a href={url}>{breadcrumbMap[url]}</a>
          ),
        });
      }
    });

    return breadcrumbItems;
  };

  return (
    <AntdLayout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        style={{
          background: '#fff',
          boxShadow: '2px 0 8px 0 rgba(29,35,41,.05)',
        }}
      >
        <div style={{ 
          height: 64, 
          padding: '16px', 
          display: 'flex', 
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0' 
        }}>
          {!collapsed && (
            <Title level={4} style={{ margin: 0, color: '#1890ff' }}>
              AWR Analyzer
            </Title>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </Sider>
      
      <AntdLayout>
        <Header
          style={{
            background: '#fff',
            padding: '0 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px 0 rgba(29,35,41,.05)',
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 64,
              height: 64,
            }}
          />
          
          <Space>
            <Dropdown 
              menu={{ 
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }} 
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <span>管理员</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        
        <Content style={{ margin: '16px' }}>
          <Breadcrumb
            items={getBreadcrumbs()}
            style={{ marginBottom: 16 }}
          />
          
          <div
            style={{
              padding: 24,
              minHeight: 'calc(100vh - 140px)',
              background: '#fff',
              borderRadius: 6,
            }}
          >
            {children}
          </div>
        </Content>
      </AntdLayout>
    </AntdLayout>
  );
};

export default Layout; 