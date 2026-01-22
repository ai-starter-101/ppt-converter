// 任务详情页 - 按页展示和编辑
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Layout, Button, Typography, Space, Card, Result, Empty, Collapse, message, Tag, Upload, Steps } from 'antd';
import { ArrowLeftOutlined, SoundOutlined, DownloadOutlined, PlayCircleOutlined, UploadOutlined, FileTextOutlined } from '@ant-design/icons';
import { getTask, getSlides, generateScripts, updateScript, generateSingleScript, generateAudio, getAudioUrl, uploadPPT } from '../../api/task';
import type { Task } from '../../types';
import type { SlideData } from '../../types';
import { getStepIndex } from '../../store/useTaskStore';

const { Header, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

export const TaskPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // 刷新幻灯片数据
  const refreshSlides = () => {
    queryClient.invalidateQueries({ queryKey: ['slides', id] });
  };

  // 先获取任务基本信息
  const { data: task, isLoading: taskLoading, error: taskError } = useQuery({
    queryKey: ['task', id],
    queryFn: () => getTask(id!),
    enabled: !!id,
  });

  // 获取幻灯片数据（只有已上传 PPT 才获取）
  const { data: taskDetail, isLoading: slidesLoading } = useQuery({
    queryKey: ['slides', id],
    queryFn: () => getSlides(id!),
    enabled: !!id && task?.status !== 'pending',
  });

  const isLoading = taskLoading || slidesLoading;
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 生成所有脚本 mutation
  const generateScriptsMutation = useMutation({
    mutationFn: () => generateScripts(id!),
    onSuccess: () => {
      message.success('脚本生成完成');
      refreshSlides();
    },
    onError: (error: Error) => {
      message.error(error.message || '脚本生成失败');
    },
  });

  // 上传 PPT mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadPPT(id!, file),
    onSuccess: () => {
      message.success('PPT 上传成功');
      queryClient.invalidateQueries({ queryKey: ['task', id] });
      queryClient.invalidateQueries({ queryKey: ['slides', id] });
    },
    onError: (error: Error) => {
      message.error(error.message || '上传失败');
    },
    onSettled: () => {
      setUploading(false);
    },
  });

  const handleBack = () => {
    navigate('/');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.pptx')) {
        message.error('只支持 .pptx 格式');
        return;
      }
      setUploading(true);
      uploadMutation.mutate(file);
    }
  };

  const triggerUpload = () => {
    fileInputRef.current?.click();
  };

  // 步骤配置
  const steps = [
    { title: '上传PPT', icon: <UploadOutlined /> },
    { title: '脚本生成', icon: <FileTextOutlined /> },
    { title: '音频生成', icon: <SoundOutlined /> },
  ];

  // 加载状态
  if (isLoading || taskLoading) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Content style={{ padding: '24px' }}>
          <Card loading />
        </Content>
      </Layout>
    );
  }

  // 错误状态
  if (taskError) {
    const errorMessage = taskError instanceof Error ? taskError.message : '加载失败';
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Content style={{ padding: '24px' }}>
          <Result
            status="error"
            title="加载失败"
            subTitle={errorMessage}
            extra={<Button onClick={handleBack}>返回首页</Button>}
          />
        </Content>
      </Layout>
    );
  }

  // 待上传状态 - 显示上传界面
  if (!task || task.status === 'pending') {
    const stepIndex = getStepIndex('pending');
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
              返回
            </Button>
            <Title level={4} style={{ margin: 0 }}>新任务</Title>
          </Space>
        </Header>
        <Content style={{ padding: '24px', maxWidth: 800, margin: '0 auto', width: '100%' }}>
          <Steps current={stepIndex} items={steps} style={{ marginBottom: 40 }} />
          <Card style={{ textAlign: 'center', padding: '40px 0' }}>
            <input
              type="file"
              ref={fileInputRef}
              accept=".pptx"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            <div style={{ marginBottom: 16 }}>
              <UploadOutlined style={{ fontSize: 64, color: '#1890ff' }} />
            </div>
            <Title level={4}>上传 PPT 文件</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
              支持 .pptx 格式的文件
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<UploadOutlined />}
              onClick={triggerUpload}
              loading={uploading}
            >
              选择文件
            </Button>
          </Card>
        </Content>
      </Layout>
    );
  }

  // 根据任务状态计算当前步骤
  const currentStep = task ? getStepIndex(task.status) : 0;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        background: '#fff',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        borderBottom: '1px solid #f0f0f0',
      }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>{task.filename || '任务详情'}</Title>
        </Space>
      </Header>

      <Content style={{ padding: '24px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
        {/* 步骤条 */}
        <Card style={{ marginBottom: '24px' }}>
          <Steps current={currentStep} items={steps} />
        </Card>

        {/* 操作按钮 */}
        <Card style={{ marginBottom: '24px' }}>
          <Space wrap>
            <Button
              type="primary"
              onClick={() => generateScriptsMutation.mutate()}
              loading={generateScriptsMutation.isPending}
              disabled={task.status === 'pending'}
            >
              {generateScriptsMutation.isPending ? '生成中...' : '批量生成脚本'}
            </Button>
          </Space>
        </Card>

        {/* 幻灯片列表 */}
        <div>
          <Title level={4}>幻灯片 ({taskDetail.slides.length} 页)</Title>

          {taskDetail.slides.length === 0 ? (
            <Empty description="暂无幻灯片数据" />
          ) : (
            <Collapse
              accordion
              defaultActiveKey={['1']}
              items={taskDetail.slides.map((slide: SlideData) => ({
                key: slide.page_num,
                label: (
                  <Space>
                    <Text strong>第 {slide.page_num} 页</Text>
                    {slide.script && <Tag color="blue">已生成脚本</Tag>}
                    {slide.audio && <Tag color="green">已生成音频</Tag>}
                  </Space>
                ),
                children: (
                  <SlideCard
                    taskId={id!}
                    slide={slide}
                    onUpdate={() => {
                      queryClient.invalidateQueries({ queryKey: ['slides', id] });
                    }}
                  />
                ),
              }))}
            />
          )}
        </div>
      </Content>
    </Layout>
  );
};

// 幻灯片卡片组件
const SlideCard = ({ taskId, slide, onUpdate }: { taskId: string; slide: SlideData; onUpdate: () => void }) => {
  const [script, setScript] = useState(slide.script || '');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  // 更新脚本 mutation
  const updateScriptMutation = useMutation({
    mutationFn: (newScript: string) => updateScript(taskId, slide.page_num, newScript),
    onSuccess: () => {
      message.success('脚本已保存');
      onUpdate();
    },
    onError: (error: Error) => {
      message.error(error.message || '保存失败');
    },
  });

  // 生成脚本 mutation
  const generateScriptMutation = useMutation({
    mutationFn: () => generateSingleScript(taskId, slide.page_num),
    onSuccess: (data: { script: string }) => {
      setScript(data.script);
      message.success('脚本生成成功');
      onUpdate();
    },
    onError: (error: Error) => {
      message.error(error.message || '生成失败');
    },
  });

  // 生成音频 mutation
  const generateAudioMutation = useMutation({
    mutationFn: () => generateAudio(taskId, slide.page_num),
    onSuccess: () => {
      setAudioUrl(getAudioUrl(taskId, slide.page_num));
      message.success('音频生成成功');
      onUpdate();
    },
    onError: (error: Error) => {
      message.error(error.message || '音频生成失败');
    },
  });

  const handleSave = () => {
    updateScriptMutation.mutate(script);
  };

  const handleGenerateScript = () => {
    generateScriptMutation.mutate();
  };

  const handleGenerateAudio = () => {
    if (!script.trim()) {
      message.warning('请先生成或编辑脚本');
      return;
    }
    generateAudioMutation.mutate();
  };

  const handleDownload = () => {
    if (!audioUrl && slide.audio?.audio_path) {
      setAudioUrl(getAudioUrl(taskId, slide.page_num));
    }
    if (audioUrl) {
      const link = document.createElement('a');
      link.href = audioUrl;
      link.download = `${taskId}_page_${slide.page_num}.mp3`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  // 设置音频 URL
  useEffect(() => {
    if (slide.audio?.audio_path) {
      setAudioUrl(getAudioUrl(taskId, slide.page_num));
    }
  }, [slide.audio, taskId, slide.page_num]);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Text strong>幻灯片内容：</Text>
        <Paragraph
          copyable
          style={{
            marginTop: 8,
            padding: 12,
            background: '#f5f5f5',
            borderRadius: 4,
            whiteSpace: 'pre-wrap',
          }}
        >
          {slide.content || '[无文本内容]'}
        </Paragraph>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 8 }}>
          <Text strong>讲解脚本：</Text>
          <Button
            size="small"
            onClick={handleGenerateScript}
            loading={generateScriptMutation.isPending}
          >
            AI 生成
          </Button>
        </Space>
        <textarea
          value={script}
          onChange={(e) => setScript(e.target.value)}
          style={{
            width: '100%',
            minHeight: 100,
            padding: 12,
            borderRadius: 4,
            border: '1px solid #d9d9d9',
            resize: 'vertical',
          }}
          placeholder="输入或生成讲解脚本..."
        />
        <div style={{ marginTop: 8 }}>
          <Button
            type="primary"
            onClick={handleSave}
            loading={updateScriptMutation.isPending}
          >
            保存脚本
          </Button>
        </div>
      </div>

      <div>
        <Space style={{ marginBottom: 8 }}>
          <Text strong>音频：</Text>
          {!slide.audio ? (
            <Button
              type="primary"
              icon={<SoundOutlined />}
              onClick={handleGenerateAudio}
              loading={generateAudioMutation.isPending}
              disabled={!script.trim()}
            >
              {generateAudioMutation.isPending ? '生成中...' : '生成音频'}
            </Button>
          ) : (
            <>
              <Tag color="green">已生成 ({Math.round(slide.audio.duration)}秒)</Tag>
              <Button
                icon={<PlayCircleOutlined />}
                onClick={() => setAudioUrl(getAudioUrl(taskId, slide.page_num))}
              >
                播放
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleDownload}
              >
                下载
              </Button>
              <Button
                icon={<SoundOutlined />}
                onClick={handleGenerateAudio}
                loading={generateAudioMutation.isPending}
              >
                重新生成
              </Button>
            </>
          )}
        </Space>

        {audioUrl && (
          <audio
            src={audioUrl}
            controls
            style={{ width: '100%', marginTop: 8 }}
          />
        )}
      </div>
    </div>
  );
};
