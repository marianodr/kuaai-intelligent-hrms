import { Controller, Get, Post, Body, Param, Query, UseGuards } from '@nestjs/common';
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
  ) {
    return this.proxy.get(`/agent/history/${userId}?limit=${limit}`);
  }
}
