import React, { useEffect } from 'react';
import { Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import { UploadOutlined, UnorderedListOutlined } from '@ant-design/icons';
import Upload from './pages/Upload';
import MeetingList from './pages/MeetingList';
import MeetingDetail from './pages/MeetingDetail';
import type { MenuProps } from 'antd';

const { Header, Content, Sider } = Layout;

// 菜单项类型
interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path: string;
}

function App(): React.ReactElement {
  const location = useLocation();
  const navigate = useNavigate();

  // 根据路由设置页面标题
  useEffect(() => {
    const titles: Record<string, string> = {
      '/': '上传音频',
      '/upload': '上传音频',
      '/meetings': '会议列表',
    };
    
    const meetingDetailMatch: RegExpMatchArray | null = location.pathname.match(/^\/meeting\/(.+)$/);
    let title: string = '会议详情';
    
    if (titles[location.pathname]) {
      title = titles[location.pathname];
    } else if (meetingDetailMatch) {
      title = '会议详情';
    }
    
    document.title = `${title} - 会议纪要系统`;
  }, [location.pathname]);

  // 确定当前选中的菜单项
  const getSelectedKey = (): string => {
    if (location.pathname === '/' || location.pathname === '/upload') {
      return 'upload';
    }
    if (location.pathname === '/meetings' || location.pathname.startsWith('/meeting/')) {
      return 'meetings';
    }
    return '';
  };

  const menuItems: MenuItem[] = [
    {
      key: 'upload',
      icon: <UploadOutlined />,
      label: '上传音频',
      path: '/',
    },
    {
      key: 'meetings',
      icon: <UnorderedListOutlined />,
      label: '会议列表',
      path: '/meetings',
    },
  ];

  // 转换为 Ant Design Menu 组件需要的格式
  const menuItemsForMenu: MenuProps['items'] = menuItems.map((item: MenuItem) => ({
    key: item.key,
    icon: item.icon,
    label: item.label,
  }));

  // 菜单点击处理
  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    const menuItem: MenuItem | undefined = menuItems.find((m: MenuItem) => m.key === key);
    if (menuItem) {
      navigate(menuItem.path);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={200}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: 'white', fontSize: '18px', fontWeight: 'bold' }}>
            会议纪要系统
          </span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItemsForMenu}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px' }} />
        <Content style={{ margin: '24px', background: '#fff', padding: 24, minHeight: 280 }}>
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/meetings" element={<MeetingList />} />
            <Route path="/meeting/:id" element={<MeetingDetail />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
