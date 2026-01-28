// 首页 - 任务列表
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, Button, Tag, Typography, Space, message, Modal, Layout, Pagination, Flex, Card } from 'antd';
import { PlusOutlined, FileTextOutlined, ClockCircleOutlined, DeleteOutlined, FolderOpenOutlined, CheckCircleFilled, SyncOutlined, RightOutlined } from '@ant-design/icons';
import { getTaskList, createTask, deleteTask } from '../../api/task';
import type { Task, TaskStatus } from '../../types';
import { useTaskStore } from '../../store/useTaskStore';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

const statusConfig: Record<TaskStatus, { color: string; text: string; icon: React.ReactNode }> = {
  pending: { color: 'default', text: '待上传', icon: <FolderOpenOutlined /> },
  uploaded: { color: 'processing', text: '已上传', icon: <FileTextOutlined /> },
  processing: { color: 'warning', text: '处理中', icon: <SyncOutlined spin /> },
  script_ready: { color: 'cyan', text: '脚本就绪', icon: <FileTextOutlined /> },
  audio_ready: { color: 'success', text: '已完成', icon: <CheckCircleFilled /> },
  video_ready: { color: 'purple', text: '已合成', icon: <FileTextOutlined /> },
  failed: { color: 'error', text: '失败', icon: <FileTextOutlined /> },
};

const getProgress = (status: TaskStatus): number => {
  switch (status) {
    case 'pending': return 0;
    case 'uploaded': return 25;
    case 'processing': return 50;
    case 'script_ready': return 75;
    case 'audio_ready': return 100;
    case 'video_ready': return 100;
    case 'failed': return 100;
    default: return 0;
  }
};

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const HomePage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setTasks, tasks } = useTaskStore();
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // 获取任务列表
  const { data: taskList, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTaskList,
  });

  // 同步到 store
  useEffect(() => {
    if (taskList) {
      setTasks(taskList);
    }
  }, [taskList, setTasks]);

  // 分页数据
  const paginatedTasks = tasks.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.ceil(tasks.length / pageSize);

  // 创建任务 mutation
  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: (data) => {
      message.success('任务创建成功');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      navigate(`/task/${data.id}`);
    },
    onError: (error: Error) => {
      message.error(error.message || '创建任务失败');
    },
  });

  const handleCreateTask = () => {
    createMutation.mutate();
  };

  // 删除任务 mutation
  const deleteMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: () => {
      message.success('任务已删除');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: (error: Error) => {
      message.error(error.message || '删除失败');
    },
  });

  const handleDeleteTask = (taskId: string, filename: string) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除任务 "${filename}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        deleteMutation.mutate(taskId);
      },
    });
  };

  // 表格列定义
  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (filename: string, record: Task) => (
        <Space>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 6,
            background: record.status === 'audio_ready' ? '#f6ffed' : '#f5f5f5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <FileTextOutlined style={{ color: record.status === 'audio_ready' ? '#52c41a' : '#666' }} />
          </div>
          <span style={{ fontWeight: 500 }}>{filename || '未命名任务'}</span>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: TaskStatus) => {
        const config = statusConfig[status];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 140,
      render: (_: unknown, record: Task) => {
        const progress = getProgress(record.status);
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              flex: 1,
              height: 6,
              background: '#f0f0f0',
              borderRadius: 3,
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${progress}%`,
                height: '100%',
                background: record.status === 'failed' ? '#ff4d4f' : '#1890ff',
                borderRadius: 3,
                transition: 'width 0.3s',
              }} />
            </div>
            <Text type="secondary" style={{ fontSize: 12, width: 32 }}>{progress}%</Text>
          </div>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (created_at: string) => (
        <Text type="secondary">
          <ClockCircleOutlined style={{ marginRight: 4 }} />
          {formatDate(created_at)}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: Task) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<RightOutlined />}
            onClick={() => navigate(`/task/${record.id}`)}
          >
            详情
          </Button>
          <Button
            type="link"
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              handleDeleteTask(record.id, record.filename || '未命名任务');
            }}
          />
        </Space>
      ),
    },
  ];

  // 空状态
  if (tasks.length === 0 && !isLoading) {
    return (
      <Layout style={{ minHeight: '100vh', background: '#f0f2f5', width: '100%' }}>
        <Header style={{
          background: '#fff',
          padding: '0 16px',
          display: 'flex',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
          width: '100%',
        }}>
          <Title level={4} style={{ margin: 0 }}>PPT 讲解生成器</Title>
        </Header>
        <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 'calc(100vh - 64px)' }}>
          <Card style={{ width: 480, textAlign: 'center', padding: '48px 32px' }}>
            <div style={{ marginBottom: 24 }}>
              <div style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: '#e6f4ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto',
              }}>
                <FileTextOutlined style={{ fontSize: 36, color: '#1890ff' }} />
              </div>
            </div>
            <Title level={4}>PPT 讲解生成器</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
              将 PowerPoint 转换为带讲解脚本和语音的演示文稿
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<PlusOutlined />}
              onClick={handleCreateTask}
              loading={createMutation.isPending}
            >
              新建任务
            </Button>
          </Card>
        </Content>
      </Layout>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5', width: '100%' }}>
      <Header style={{
        background: '#fff',
        padding: '0 16px',
        display: 'flex',
        alignItems: 'center',
        borderBottom: '1px solid #f0f0f0',
        width: '100%',
      }}>
        <Flex justify="space-between" align="center" style={{ width: '100%' }}>
          <Title level={4} style={{ margin: 0 }}>PPT 讲解生成器</Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateTask}
            loading={createMutation.isPending}
          >
            新建任务
          </Button>
        </Flex>
      </Header>

      <Content style={{ padding: 0, height: 'calc(100vh - 64px)', overflow: 'auto' }}>
        <div style={{ width: '100%' }}>
          {/* 任务表格 */}
          <Card style={{ marginBottom: 16, width: '100%' }}>
            <Flex justify="space-between" align="center" style={{ marginBottom: 16 }}>
              <Title level={5} style={{ margin: 0 }}>任务列表</Title>
              <Text type="secondary">共 {tasks.length} 个任务</Text>
            </Flex>

            <Table
              dataSource={paginatedTasks}
              columns={columns}
              rowKey="id"
              loading={isLoading}
              pagination={false}
              size="middle"
              scroll={{ x: true }}
              onRow={(record) => ({
                onClick: () => navigate(`/task/${record.id}`),
                style: { cursor: 'pointer' },
              })}
              style={{ width: '100%' }}
            />

            {totalPages > 1 && (
              <Flex justify="center" style={{ marginTop: 16 }}>
                <Pagination
                  current={page}
                  total={tasks.length}
                  pageSize={pageSize}
                  onChange={(p) => setPage(p)}
                  showSizeChanger={false}
                  showTotal={(total) => `共 ${total} 个任务`}
                />
              </Flex>
            )}
          </Card>
        </div>
      </Content>
    </Layout>
  );
};
