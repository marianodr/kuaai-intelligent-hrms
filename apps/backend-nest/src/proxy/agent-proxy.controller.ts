import { Controller, Get, Post, Patch, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ProxyService } from './proxy.service';

@UseGuards(JwtAuthGuard)
@Controller('agent')
export class AgentProxyController {
  constructor(private readonly proxy: ProxyService) {}

  @Post('chat')
  chat(
    @Body() body: { question: string; user_id: number; thread_id?: string },
  ) {
    return this.proxy.post('/agent/chat', body);
  }

  @Get('history/:userId')
  history(
    @Param('userId') userId: string,
    @Query('limit') limit = '50',
    @Query('thread_id') threadId?: string,
  ) {
    const qs = threadId
      ? `/agent/history/${userId}?limit=${limit}&thread_id=${threadId}`
      : `/agent/history/${userId}?limit=${limit}`;
    return this.proxy.get(qs);
  }
}

@UseGuards(JwtAuthGuard)
@Controller('threads')
export class ThreadsProxyController {
  constructor(private readonly proxy: ProxyService) {}

  @Post()
  create(@Body() body: { user_id: number; name?: string }) {
    return this.proxy.post('/threads/', body);
  }

  @Get(':userId')
  list(@Param('userId') userId: string) {
    return this.proxy.get(`/threads/${userId}`);
  }

  @Patch(':threadId/rename')
  rename(@Param('threadId') threadId: string, @Body() body: { name: string }) {
    return this.proxy.patch(`/threads/${threadId}/rename`, body);
  }

  @Delete(':threadId')
  remove(@Param('threadId') threadId: string) {
    return this.proxy.delete(`/threads/${threadId}`);
  }
}
