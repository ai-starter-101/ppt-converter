// 首页 - 任务列表
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, Button, List, Tag, Typography, Empty, Space, message, Modal } from 'antd';
import { PlusOutlined, FileTextOutlined, ClockCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import { getTaskList, createTask, deleteTask } from '../../api/task';
import type { Task, TaskStatus } from '../../types';
import { useTaskStore } from '../../store/useTaskStore';

const { Title, Text } = Typography;

const statusConfig: Record<TaskStatus, { color: string; text: string }> = {
  pending: { color: 'default', text: '待上传' },
  uploaded: { color: 'processing', text: '已上传' },
  processing: { color: 'warning', text: '处理中' },
  script_ready: { color: 'cyan', text: '脚本就绪' },
  audio_ready: { color: 'success', text: '已完成' },
  failed: { color: 'error', text: '失败' },
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

  const handleOpenTask = (taskId: string) => {
    navigate(`/task/${taskId}`);
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

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2} style={{ margin: 0 }}>PPT 讲解生成器</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          size="large"
          onClick={handleCreateTask}
          loading={createMutation.isPending}
        >
          新建任务
        </Button>
      </div>

      <Card>
        {tasks.length === 0 && !isLoading ? (
          <Empty
            description="暂无任务，点击新建任务开始"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button type="primary" onClick={handleCreateTask}>
              新建任务
            </Button>
          </Empty>
        ) : (
          <List
            loading={isLoading}
            dataSource={tasks}
            renderItem={(task: Task) => {
              const config = statusConfig[task.status];
              return (
                <List.Item
                  actions={[
                    <Button type="link" onClick={() => handleOpenTask(task.id)}>
                      打开
                    </Button>,
                    <Button
                      type="link"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDeleteTask(task.id, task.filename || '未命名任务')}
                      loading={deleteMutation.isPending}
                    >
                      删除
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      <div style={{
                        width: 48,
                        height: 48,
                        background: '#f0f0f0',
                        borderRadius: 8,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <FileTextOutlined style={{ fontSize: 24, color: '#666' }} />
                      </div>
                    }
                    title={
                      <Space>
                        <span>{task.filename}</span>
                        <Tag color={config.color}>{config.text}</Tag>
                      </Space>
                    }
                    description={
                      <Space>
                        <ClockCircleOutlined />
                        <Text type="secondary">{formatDate(task.created_at)}</Text>
                      </Space>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Card>
    </div>
  );
};
