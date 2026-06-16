import {
  Controller, Get, Post, Delete,
  Param, Body, UploadedFile,
  UseGuards, UseInterceptors, Res,
} from '@nestjs/common';
import { Response } from 'express';
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

  @Get(':id/download')
  async download(@Param('id') id: string, @Res() res: Response) {
    const { data, contentType } = await this.proxy.downloadBinary(`/documents/${id}/download`);
    res.set('Content-Type', contentType);
    res.set('Content-Disposition', 'inline');
    res.send(data);
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
