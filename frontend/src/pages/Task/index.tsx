// 任务详情页 - 走马灯形式展示和编辑
import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Layout, Button, Typography, Space, Card, Result, message, Tag, Steps, Flex, Carousel, Upload, Modal, Progress } from 'antd';
import type { CarouselRef } from 'antd/es/carousel';
import {
  ArrowLeftOutlined,
  SoundOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  SaveOutlined,
  ReloadOutlined,
  CheckCircleFilled,
  LeftOutlined,
  RightOutlined,
  VideoCameraOutlined,
  FileAddOutlined,
  PictureOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { getTask, getSlides, generateScripts, updateScript, generateSingleScript, generateAudio, getAudioUrl, uploadPPT, generateAllAudioStream, synthesizeVideo, uploadScreenshots } from '../../api/task';
import type { SlideData } from '../../types';
import { getStepIndex } from '../../store/useTaskStore';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

// 步骤配置
const steps = [
  { title: '上传PPT', icon: <FileTextOutlined /> },
  { title: '脚本/音频', icon: <SoundOutlined /> },
  { title: '合成视频', icon: <VideoCameraOutlined /> },
];

export const TaskPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const carouselRef = useRef<CarouselRef>(null);

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
  const [currentSlide, setCurrentSlide] = useState(0);

  // 进度弹窗状态
  const [progressModalOpen, setProgressModalOpen] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressCurrent, setProgressCurrent] = useState(0);
  const [progressTotal, setProgressTotal] = useState(0);
  const [progressPageNum, setProgressPageNum] = useState<number | null>(null);
  const [progressSkipped, setProgressSkipped] = useState(0);

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

  // 流式生成所有音频
  const handleGenerateAllAudio = async () => {
    if (!id) return;

    // 计算已成功的页面数量
    const existingSuccessCount = slides.filter(s => s.audio).length;
    setProgressSkipped(existingSuccessCount);

    setProgressModalOpen(true);
    setProgressPercent(0);
    setProgressCurrent(0);
    setProgressTotal(0);
    setProgressPageNum(null);

    try {
      await generateAllAudioStream(id, (data) => {
        if (data.type === 'progress') {
          setProgressCurrent(data.current || 0);
          setProgressTotal(data.total || 0);
          setProgressPercent(data.percent || 0);
          setProgressPageNum(data.page_num || null);
        } else if (data.type === 'script_saved') {
          message.info(data.message);
          refreshSlides();
        } else if (data.type === 'complete') {
          message.success('音频批量生成完成');
          refreshSlides();
          queryClient.invalidateQueries({ queryKey: ['task', id] });
          setProgressModalOpen(false);
        }
      });
    } catch (error) {
      message.error(error instanceof Error ? error.message : '音频生成失败');
      setProgressModalOpen(false);
    }
  };

  // 合成视频 mutation
  const synthesizeVideoMutation = useMutation({
    mutationFn: () => synthesizeVideo(id!),
    onSuccess: (data) => {
      message.success('视频合成完成');
      queryClient.invalidateQueries({ queryKey: ['task', id] });
    },
    onError: (error: Error) => {
      message.error(error.message || '视频合成失败');
    },
  });

  // 上传截图 mutation
  const uploadScreenshotsMutation = useMutation({
    mutationFn: (files: File[]) => uploadScreenshots(id!, files),
    onSuccess: () => {
      message.success('截图上传成功');
      refreshSlides();
      queryClient.invalidateQueries({ queryKey: ['task', id] });
    },
    onError: (error: Error) => {
      message.error(error.message || '截图上传失败');
    },
  });

  // 处理截图上传
  const handleScreenshotsUpload = (fileList: File[]) => {
    if (fileList.length === 0) return;
    uploadScreenshotsMutation.mutate(fileList);
  };

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

  // 加载状态
  if (isLoading || taskLoading) {
    return (
      <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
        <Content style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Card loading style={{ width: 400 }} />
        </Content>
      </Layout>
    );
  }

  // 错误状态
  if (taskError) {
    const errorMessage = taskError instanceof Error ? taskError.message : '加载失败';
    return (
      <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
        <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
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
    return (
      <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
        <Header style={{
          background: '#fff',
          padding: '0 16px',
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
        <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 'calc(100vh - 64px)' }}>
          <Card style={{ width: 480, textAlign: 'center', padding: '48px 32px' }}>
            <input
              type="file"
              ref={fileInputRef}
              accept=".pptx"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
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
            <Title level={4}>上传 PPT 文件</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
              支持 .pptx 格式的文件
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<FileTextOutlined />}
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

  const slides = taskDetail?.slides || [];
  const currentSlideData = slides[currentSlide];

  // 计算进度
  const audioGeneratedCount = slides.filter(s => s.audio).length;
  const audioProgress = slides.length > 0 ? Math.round((audioGeneratedCount / slides.length) * 100) : 0;

  // 检查是否已合成视频
  const isVideoReady = task.status === 'video_ready';

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Header style={{
        background: '#fff',
        padding: '0 16px',
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

      <Content style={{ padding: 16, height: 'calc(100vh - 64px)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* 顶部区域：步骤条 + 操作栏 */}
        <Card style={{ marginBottom: 12, flexShrink: 0 }}>
          <Flex justify="space-between" align="center" wrap gap={12}>
            <Steps current={currentStep} items={steps} size="small" style={{ flex: 1, minWidth: 300 }} />
            <Space wrap>
              {/* 步骤1操作 */}
              {currentStep === 1 && (
                <>
                  <Button
                    type="primary"
                    icon={<FileTextOutlined />}
                    onClick={() => generateScriptsMutation.mutate()}
                    loading={generateScriptsMutation.isPending}
                  >
                    批量生成脚本
                  </Button>
                  <Button
                    icon={<SoundOutlined />}
                    onClick={handleGenerateAllAudio}
                    disabled={slides.every(s => s.audio)}
                  >
                    批量生成音频
                  </Button>
                  <Text type="secondary">
                    音频: {audioGeneratedCount}/{slides.length} ({audioProgress}%)
                  </Text>
                </>
              )}
              {/* 步骤2操作 */}
              {currentStep === 2 && (
                <>
                  {/* 上传截图按钮 */}
                  <Upload
                    accept="image/*"
                    multiple
                    showUploadList={false}
                    onChange={({ fileList }) => {
                      const files = fileList.map(f => f.originFileObj!).filter(Boolean);
                      if (files.length > 0) {
                        handleScreenshotsUpload(files);
                      }
                    }}
                  >
                    <Button icon={<PictureOutlined />}>
                      上传截图
                    </Button>
                  </Upload>
                  <Text type="secondary">
                    (支持: 幻灯片1.jpeg, page_1.png, slide_1.png)
                  </Text>

                  {isVideoReady ? (
                    <Tag color="success" icon={<CheckCircleFilled />} style={{ fontSize: 14, padding: '4px 12px' }}>
                      视频已合成
                    </Tag>
                  ) : (
                    <Button
                      type="primary"
                      icon={<VideoCameraOutlined />}
                      onClick={() => synthesizeVideoMutation.mutate()}
                      loading={synthesizeVideoMutation.isPending}
                      disabled={audioGeneratedCount < slides.length}
                    >
                      合成视频
                    </Button>
                  )}
                  <Button
                    icon={<ReloadOutlined spin={synthesizeVideoMutation.isPending} />}
                    onClick={() => synthesizeVideoMutation.mutate()}
                    loading={synthesizeVideoMutation.isPending}
                    disabled={audioGeneratedCount < slides.length}
                  >
                    重新合成
                  </Button>
                  {task.video_path && (
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => {
                        const link = document.createElement('a');
                        // 从 task.video_path 提取文件名
                        const videoFilename = task.video_path.split('/').pop();
                        // 使用后端完整 URL
                        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
                        const baseUrl = apiBaseUrl.replace('/api', '');
                        link.href = `${baseUrl}/static/video/${id}/${videoFilename}`;
                        link.download = videoFilename;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                      }}
                    >
                      下载视频
                    </Button>
                  )}
                </>
              )}
            </Space>
          </Flex>
        </Card>

        {/* 幻灯片走马灯 */}
        <Card style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {/* 走马灯导航 */}
          <Flex justify="space-between" align="center" style={{ marginBottom: 12 }}>
            <Button
              icon={<LeftOutlined />}
              onClick={() => carouselRef.current?.prev()}
              disabled={currentSlide === 0}
            >
              上一页
            </Button>
            <Space>
              <span style={{
                background: '#1890ff',
                color: '#fff',
                padding: '4px 12px',
                borderRadius: 16,
                fontSize: 14,
              }}>
                {currentSlide + 1} / {slides.length}
              </span>
              {currentSlideData?.script && (
                <Tag color="blue" icon={<CheckCircleFilled />}>脚本</Tag>
              )}
              {currentSlideData?.audio && (
                <Tag color="green" icon={<CheckCircleFilled />}>
                  音频 {Math.round(currentSlideData.audio.duration)}s
                </Tag>
              )}
            </Space>
            <Button
              onClick={() => carouselRef.current?.next()}
              disabled={currentSlide >= slides.length - 1}
            >
              下一页 <RightOutlined />
            </Button>
          </Flex>

          {/* 走马灯 */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <Carousel
              ref={carouselRef}
              beforeChange={(_, newSlide) => setCurrentSlide(newSlide)}
              style={{ height: '100%' }}
            >
              {slides.map((slide: SlideData) => (
                <div key={slide.page_num} style={{ height: '100%' }}>
                  <SlideCard
                    taskId={id!}
                    slide={slide}
                    onUpdate={() => {
                      queryClient.invalidateQueries({ queryKey: ['slides', id] });
                    }}
                  />
                </div>
              ))}
            </Carousel>
          </div>
        </Card>
      </Content>

      {/* 进度弹窗 */}
      <Modal
        title="生成音频中..."
        open={progressModalOpen}
        closable={false}
        footer={null}
        maskClosable={false}
        width={400}
      >
        <div style={{ padding: '16px 0' }}>
          <Progress
            percent={progressPercent}
            status="active"
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          <div style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
            {progressPageNum ? (
              <span>正在生成第 {progressPageNum} 页音频...</span>
            ) : (
              <span>准备中...</span>
            )}
          </div>
          <div style={{ marginTop: 8, textAlign: 'center', color: '#999', fontSize: 12 }}>
            {progressCurrent} / {progressTotal} 页
            {progressSkipped > 0 && (
              <span style={{ marginLeft: 12, color: '#52c41a' }}>
                (已跳过 {progressSkipped} 个成功页面)
              </span>
            )}
          </div>
        </div>
      </Modal>
    </Layout>
  );
};

// 幻灯片卡片组件 - 左右各50%布局
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
      // 添加时间戳避免缓存
      setAudioUrl(`${getAudioUrl(taskId, slide.page_num)}?t=${Date.now()}`);
      message.success('音频生成成功');
      onUpdate();
    },
    onError: (error: Error) => {
      message.error(error.message || '音频生成失败');
    },
  });

  // 强制重新生成音频（不管是否已有音频）
  const handleForceRegenerateAudio = () => {
    // 检查脚本是否发生变化
    const originalScript = slide.content || '';
    if (script.trim() === originalScript.trim()) {
      message.warning('脚本未修改，不需要重新生成音频！');
      return;
    }
    forceRegenerateMutation.mutate();
  };

  const forceRegenerateMutation = useMutation({
    mutationFn: async () => {
      // 先删除旧音频，再生成新的
      await generateAudio(taskId, slide.page_num);
    },
    onSuccess: () => {
      // 添加时间戳避免缓存
      setAudioUrl(`${getAudioUrl(taskId, slide.page_num)}?t=${Date.now()}`);
      message.success('音频重新生成成功');
      onUpdate();
    },
    onError: (error: Error) => {
      message.error(error.message || '音频重新生成失败');
    },
  });

  const handleSave = () => {
    updateScriptMutation.mutate(script);
  };

  const handleGenerateScript = () => {
    generateScriptMutation.mutate();
  };

  const handleGenerateAudio = () => {
    // 如果已有音频，直接播放
    if (slide.audio?.audio_path) {
      const url = getAudioUrl(taskId, slide.page_num);
      setAudioUrl(url);
      // 播放音频
      setTimeout(() => {
        const audio = document.getElementById(`audio-${taskId}-${slide.page_num}`) as HTMLAudioElement;
        audio?.play().catch(() => {});
      }, 100);
      message.success('音频已准备，点击播放按钮即可收听');
      return;
    }
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
      // 添加时间戳避免缓存
      setAudioUrl(`${getAudioUrl(taskId, slide.page_num)}?t=${Date.now()}`);
    }
  }, [slide.audio, taskId, slide.page_num]);

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* 左侧：幻灯片预览 - 50% */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Text strong style={{ marginBottom: 8 }}>幻灯片预览</Text>
        <div style={{ flex: 1, overflow: 'auto', background: '#f5f5f5', borderRadius: 8, padding: 12 }}>
          {slide.screenshot ? (
            <img
              src={slide.screenshot}
              alt={`第 ${slide.page_num} 页`}
              style={{
                width: '100%',
                borderRadius: 6,
                border: '1px solid #d9d9d9',
                display: 'block',
              }}
            />
          ) : (
            <div
              style={{
                padding: 12,
                background: '#fff',
                borderRadius: 6,
                fontSize: 13,
                minHeight: 200,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                border: '1px solid #d9d9d9',
              }}
            >
              {slide.content || '[无文本内容]'}
            </div>
          )}
        </div>
      </div>

      {/* 右侧：脚本编辑 + 音频 - 50% */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* 脚本编辑区 */}
        <Card
          size="small"
          title={
            <Flex justify="space-between" align="center">
              <Space>
                <FileTextOutlined style={{ color: '#1890ff' }} />
                <span>讲解脚本</span>
                {slide.script && slide.script !== slide.content && (
                  <Tag color="blue">已生成</Tag>
                )}
              </Space>
              <Button
                size="small"
                icon={<ReloadOutlined spin={generateScriptMutation.isPending} />}
                onClick={handleGenerateScript}
                loading={generateScriptMutation.isPending}
              >
                AI 生成
              </Button>
            </Flex>
          }
          bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 12 }}
          style={{ flex: 1, marginBottom: 12, display: 'flex', flexDirection: 'column' }}
        >
          <textarea
            value={script}
            onChange={(e) => setScript(e.target.value)}
            style={{
              flex: 1,
              width: '100%',
              padding: 12,
              borderRadius: 6,
              border: '1px solid #d9d9d9',
              resize: 'none',
              fontSize: 14,
              lineHeight: 1.6,
              minHeight: 150,
            }}
            placeholder="输入或生成讲解脚本..."
          />
          <Flex justify="flex-end" style={{ marginTop: 12 }}>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={updateScriptMutation.isPending}
              disabled={!script.trim()}
            >
              保存脚本
            </Button>
          </Flex>
        </Card>

        {/* 音频区 */}
        <Card
          size="small"
          title={
            <Flex justify="space-between" align="center">
              <Space>
                <SoundOutlined style={{ color: '#52c41a' }} />
                <span>语音音频</span>
              </Space>
              {!slide.audio && (
                <Button
                  type="primary"
                  size="small"
                  icon={<SoundOutlined />}
                  onClick={handleGenerateAudio}
                  loading={generateAudioMutation.isPending}
                  disabled={!script.trim() && !slide.audio?.audio_path}
                >
                  生成音频
                </Button>
              )}
            </Flex>
          }
          bodyStyle={{ padding: 12 }}
        >
          {slide.audio ? (
            <div>
              <Flex align="center" gap={8} wrap style={{ marginBottom: 12 }}>
                <Tag color="success" icon={<CheckCircleFilled />}>
                  已生成 {Math.round(slide.audio.duration)} 秒
                </Tag>
                <Button
                  size="small"
                  icon={<PlayCircleOutlined />}
                  onClick={() => {
                    const url = getAudioUrl(taskId, slide.page_num);
                    setAudioUrl(url);
                    setTimeout(() => {
                      const audio = document.getElementById(`audio-${taskId}-${slide.page_num}`) as HTMLAudioElement;
                      audio?.play().catch(() => {});
                    }, 100);
                  }}
                >
                  播放
                </Button>
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={handleDownload}
                >
                  下载
                </Button>
                <Button
                  size="small"
                  icon={<ReloadOutlined spin={generateAudioMutation.isPending} />}
                  onClick={handleGenerateAudio}
                  loading={generateAudioMutation.isPending}
                >
                  播放
                </Button>
                <Button
                  size="small"
                  icon={<SyncOutlined spin={forceRegenerateMutation.isPending} />}
                  onClick={handleForceRegenerateAudio}
                  loading={forceRegenerateMutation.isPending}
                  danger
                >
                  重新生成
                </Button>
              </Flex>
              {audioUrl && (
                <audio
                  id={`audio-${taskId}-${slide.page_num}`}
                  src={audioUrl}
                  controls
                  style={{ width: '100%', marginTop: 8 }}
                />
              )}
            </div>
          ) : (
            <Flex align="center" justify="center" style={{ padding: 24, color: '#999', background: '#fafafa', borderRadius: 6 }}>
              <SoundOutlined style={{ fontSize: 24, marginRight: 8 }} />
              <div>请先编辑或生成脚本，然后生成音频</div>
            </Flex>
          )}
        </Card>
      </div>
    </div>
  );
};
