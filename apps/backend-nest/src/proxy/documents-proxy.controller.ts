import {
  Controller, Get, Post, Delete,
  Param, Body, UploadedFile,
  UseGuards, UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { ProxyService } from './proxy.service';

@UseGuards(JwtAuthGuard)
@Controller('documents')
export class DocumentsProxyController {
  constructor(private readonly proxy: ProxyService) {}

  @Get()
  list() {
    return this.proxy.get('/documents/');
  }

  @Get(':id')
  get(@Param('id') id: string) {
    return this.proxy.get(`/documents/${id}`);
  }

  @Post('upload')
  @UseInterceptors(FileInterceptor('file'))
  upload(
    @UploadedFile() file: { buffer: Buffer; originalname: string; mimetype: string },
    @Body('uploaded_by') uploadedBy: string,
  ) {
    return this.proxy.uploadFile(file, uploadedBy);
  }

  @Post('process')
  process(@Body() body: { document_id: string }) {
    return this.proxy.post('/documents/process', body);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.proxy.delete(`/documents/${id}`);
  }
}
